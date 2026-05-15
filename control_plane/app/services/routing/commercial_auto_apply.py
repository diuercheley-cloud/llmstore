from __future__ import annotations

import logging
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_routing_config import CommercialRoutingConfig
from app.models.admin_action_log import AdminActionLog
from app.core.config import get_settings
from app.services.routing.commercial_config_store import CommercialConfigStore

logger = logging.getLogger(__name__)

class CommercialAutoApplyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.store = CommercialConfigStore(db)
        self.settings = get_settings()

    async def evaluate_auto_apply_candidate(
        self,
        provider: str,
        model: str,
        recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates if a recommendation is eligible for auto-apply.
        """
        reasons_rejected = []
        
        # 1. Check if globally enabled
        if not self.settings.commercial_calibration_auto_apply:
            reasons_rejected.append("Auto-apply globally disabled")

        # 2. Check confidence
        confidence = recommendation.get("confidence", "low")
        min_confidence = self.settings.commercial_calibration_auto_apply_min_confidence
        if confidence != "high" and min_confidence == "high":
            reasons_rejected.append(f"Confidence {confidence} is below required high")
        elif confidence == "low":
            reasons_rejected.append("Confidence is low")

        # 3. Check sample count
        sample_count = recommendation.get("sample_count", 0)
        if sample_count < self.settings.commercial_calibration_auto_apply_min_recent_samples:
            reasons_rejected.append(f"Sample count {sample_count} below minimum {self.settings.commercial_calibration_auto_apply_min_recent_samples}")

        # 4. Check change percent
        # cost_error_percent is the difference between current and recommended
        change_percent = abs(recommendation.get("cost_error_percent", 0))
        max_change = self.settings.commercial_calibration_auto_apply_max_change_percent
        if change_percent > max_change:
            reasons_rejected.append(f"Recommended change {change_percent:.1f}% exceeds max {max_change}%")

        # 5. Check 24h data if required
        if self.settings.commercial_calibration_auto_apply_require_24h_data:
            has_recent = await self.has_recent_data(provider, model, hours=24)
            if not has_recent:
                reasons_rejected.append("No data in the last 24 hours")

        # 6. Check rate limit
        rate_limited = await self.is_rate_limited(provider, model)
        if rate_limited:
            reasons_rejected.append("Rate limited (too many recent auto-applies)")

        is_eligible = len(reasons_rejected) == 0
        
        return {
            "eligible": is_eligible,
            "reasons_rejected": reasons_rejected,
            "provider": provider,
            "model": model,
            "recommended_multiplier": recommendation.get("recommended_multiplier"),
            "confidence": confidence,
            "sample_count": sample_count,
            "change_percent": change_percent
        }

    async def has_recent_data(self, provider: str, model: str, hours: int = 24) -> bool:
        """
        Check if there are any routing events in the last X hours.
        """
        from app.models.commercial_routing_event import CommercialRoutingEvent
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        stmt = select(func.count()).select_from(CommercialRoutingEvent).where(
            and_(
                CommercialRoutingEvent.selected_provider == provider,
                CommercialRoutingEvent.selected_model == model,
                CommercialRoutingEvent.created_at >= since
            )
        )
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def is_rate_limited(self, provider: str, model: str) -> bool:
        """
        Enforce rate limit: no more than 1 auto-apply per (provider, model) per window.
        """
        window_minutes = self.settings.commercial_calibration_auto_apply_rate_limit_minutes
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        stmt = select(func.count()).select_from(CommercialRoutingConfig).where(
            and_(
                CommercialRoutingConfig.provider == provider,
                CommercialRoutingConfig.model == model,
                CommercialRoutingConfig.auto_applied == True,
                CommercialRoutingConfig.created_at >= since
            )
        )
        result = await self.db.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def run_auto_apply(
        self,
        provider: str,
        model: str,
        recommendation: Dict[str, Any],
        actor: str = "system"
    ) -> Optional[CommercialRoutingConfig]:
        """
        Runs the auto-apply logic based on current mode (dry_run, canary).
        """
        eval_result = await self.evaluate_auto_apply_candidate(provider, model, recommendation)
        
        if not eval_result["eligible"]:
            await self._log_action(
                "auto_apply_rejected",
                status="rejected",
                payload={
                    "provider": provider,
                    "model": model,
                    "reasons": eval_result["reasons_rejected"],
                    "recommendation": recommendation
                }
            )
            return None

        mode = self.settings.commercial_calibration_auto_apply_mode
        
        if mode == "disabled":
            return None
        elif mode == "dry_run":
            await self._log_action(
                "auto_apply_dry_run",
                status="success",
                payload=eval_result
            )
            return None
        elif mode == "canary":
            return await self.apply_canary_config(provider, model, eval_result, actor=actor)
        
        return None

    async def apply_canary_config(
        self,
        provider: str,
        model: str,
        eval_result: Dict[str, Any],
        actor: str = "system"
    ) -> CommercialRoutingConfig:
        """
        Creates a new canary configuration.
        """
        canary_percent = self.settings.commercial_calibration_canary_default_percent
        
        # Get current effective config to inherit weights
        current = await self.store.get_effective_config(provider, model)
        
        new_config = CommercialRoutingConfig(
            scope_type="provider_model",
            provider=provider,
            model=model,
            cost_multiplier=eval_result["recommended_multiplier"],
            margin_weight=current["margin_weight"],
            latency_weight=current["latency_weight"],
            quality_weight=current["quality_weight"],
            local_route_bonus=current["local_route_bonus"],
            min_margin_percent=current["min_margin_percent"],
            source="calibration",
            is_active=True,
            created_by=actor,
            auto_applied=True,
            can_auto_apply=True,
            auto_apply_confidence=eval_result["confidence"],
            auto_apply_source_event_count=eval_result["sample_count"],
            auto_apply_reason=f"Auto-applied {eval_result['change_percent']:.1f}% change via canary",
            canary_enabled=True,
            canary_percent=canary_percent,
            notes=f"Auto-applied canary {canary_percent}%"
        )
        
        self.db.add(new_config)
        await self.db.flush()
        
        await self._log_action(
            "auto_apply_canary_created",
            status="success",
            payload={
                "config_id": str(new_config.id),
                "provider": provider,
                "model": model,
                "canary_percent": canary_percent,
                "multiplier": new_config.cost_multiplier
            }
        )
        
        await self.db.commit()
        return new_config

    async def promote_canary(self, config_id: uuid.UUID, actor: str = "admin") -> Optional[CommercialRoutingConfig]:
        """
        Promotes a canary config to full 100% stable config.
        """
        stmt = select(CommercialRoutingConfig).where(
            and_(
                CommercialRoutingConfig.id == config_id,
                CommercialRoutingConfig.canary_enabled == True,
                CommercialRoutingConfig.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        canary = result.scalar_one_or_none()
        
        if not canary:
            return None

        # Deactivate previous stable config for same scope
        update_stmt = (
            update(CommercialRoutingConfig)
            .where(
                and_(
                    CommercialRoutingConfig.scope_type == canary.scope_type,
                    CommercialRoutingConfig.provider == canary.provider,
                    CommercialRoutingConfig.model == canary.model,
                    CommercialRoutingConfig.is_active == True,
                    CommercialRoutingConfig.canary_enabled == False
                )
            )
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        await self.db.execute(update_stmt)

        # Update canary to be stable
        canary.canary_enabled = False
        canary.canary_percent = 0
        canary.updated_at = datetime.now(timezone.utc)
        canary.notes = (canary.notes or "") + f" | Promoted to stable by {actor}"
        
        await self._log_action(
            "auto_apply_canary_promoted",
            status="success",
            payload={
                "config_id": str(config_id),
                "provider": canary.provider,
                "model": canary.model
            }
        )
        
        await self.db.commit()
        await self.db.refresh(canary)
        return canary

    async def rollback_canary(self, config_id: uuid.UUID, actor: str = "admin") -> bool:
        """
        Immediately deactivates a canary config.
        """
        stmt = select(CommercialRoutingConfig).where(CommercialRoutingConfig.id == config_id)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            return False
            
        config.is_active = False
        config.updated_at = datetime.now(timezone.utc)
        config.notes = (config.notes or "") + f" | Rollback by {actor}"
        
        await self._log_action(
            "auto_apply_canary_rollback",
            status="success",
            payload={
                "config_id": str(config_id),
                "provider": config.provider,
                "model": config.model
            }
        )
        
        await self.db.commit()
        return True

    async def _log_action(self, action: str, status: str, payload: Dict[str, Any]):
        audit = AdminActionLog(
            action=action,
            admin_role="system",
            status=status,
            payload_json=payload
        )
        self.db.add(audit)

    @staticmethod
    def get_canary_bucket(request_id: Optional[str], correlation_id: Optional[str], client_id: Optional[str]) -> int:
        """
        Deterministic hashing for canary selection (0-99).
        """
        identifier = request_id or correlation_id or client_id
        if not identifier:
            return 100 # Should never match a canary percent (usually 5-25)
            
        hash_val = hashlib.md5(identifier.encode()).hexdigest()
        return int(hash_val, 16) % 100
