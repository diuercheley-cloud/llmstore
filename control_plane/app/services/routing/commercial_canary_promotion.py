from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.core.admin_action_log import AdminActionLog
from app.models.commercial.commercial_routing_config import CommercialRoutingConfig
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class CommercialCanaryPromotionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_canary_metrics(self, config_id: uuid.UUID, window_minutes: int = 60) -> Dict[str, Any]:
        """
        Collects metrics for a specific canary config and its stable counterpart.
        """
        config = await self.db.get(CommercialRoutingConfig, config_id)
        if not config:
            return {}

        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        # Metrics for canary
        canary_metrics = await self._query_metrics(config_id, "canary", since)
        
        # Metrics for stable (counterpart)
        # Find the active stable config for the same scope
        stable_stmt = select(CommercialRoutingConfig).where(
            CommercialRoutingConfig.scope_type == config.scope_type,
            CommercialRoutingConfig.provider == config.provider,
            CommercialRoutingConfig.model == config.model,
            CommercialRoutingConfig.is_active == True,
            CommercialRoutingConfig.canary_enabled == False,
            CommercialRoutingConfig.id != config_id
        ).order_by(desc(CommercialRoutingConfig.created_at))
        
        stable_res = await self.db.execute(stable_stmt)
        stable_config = stable_res.scalars().first()
        
        stable_metrics = {}
        if stable_config:
            stable_metrics = await self._query_metrics(stable_config.id, "stable", since)
        else:
            # If no specific stable config, try to find default events (config_variant="default")
            stable_metrics = await self._query_metrics(None, "default", since)

        return {
            "config_id": str(config_id),
            "canary": canary_metrics,
            "stable": stable_metrics,
            "window_minutes": window_minutes,
            "canary_percent": config.canary_percent
        }

    async def _query_metrics(self, config_id: Optional[uuid.UUID], variant: str, since: datetime) -> Dict[str, Any]:
        filters = [
            CommercialRoutingEvent.created_at >= since,
            CommercialRoutingEvent.commercial_config_variant == variant
        ]
        if config_id:
            filters.append(CommercialRoutingEvent.commercial_config_id == config_id)

        stmt = select(
            func.count(CommercialRoutingEvent.id).label("total"),
            func.count(CommercialRoutingEvent.id).filter(CommercialRoutingEvent.error_type.is_not(None)).label("errors"),
            func.avg(CommercialRoutingEvent.latency_ms).label("avg_latency"),
            # PostgreSQL specific percentile_cont might not be available in all backends, 
            # using a simpler avg if it fails or if not postgres. 
            # For this project, it's usually postgres.
            func.avg(CommercialRoutingEvent.actual_margin_percent).label("avg_margin"),
            func.avg(func.abs(func.coalesce(CommercialRoutingEvent.estimated_margin_percent, 0) - func.coalesce(CommercialRoutingEvent.actual_margin_percent, 0))).label("avg_est_error"),
            func.count(CommercialRoutingEvent.id).filter(CommercialRoutingEvent.fallback_used == True).label("fallbacks"),
            func.count(CommercialRoutingEvent.id).filter(CommercialRoutingEvent.blocked == True).label("blocks")
        ).where(*filters)

        res = await self.db.execute(stmt)
        row = res.one()

        total = row.total or 0
        error_rate = (row.errors / total * 100) if total > 0 else 0.0
        fallback_rate = (row.fallbacks / total * 100) if total > 0 else 0.0
        block_rate = (row.blocks / total * 100) if total > 0 else 0.0

        return {
            "request_count": total,
            "error_rate": round(error_rate, 2),
            "avg_latency_ms": round(float(row.avg_latency or 0), 2),
            "avg_margin_percent": round(float(row.avg_margin or 0), 2),
            "avg_estimation_error_percent": round(float(row.avg_est_error or 0), 2),
            "fallback_rate": round(fallback_rate, 2),
            "block_rate": round(block_rate, 2),
        }

    async def evaluate_canary_slo(self, config_id: uuid.UUID) -> Dict[str, Any]:
        config = await self.db.get(CommercialRoutingConfig, config_id)
        if not config or not config.canary_enabled:
            return {"pass": False, "reason": "Config not found or not canary"}

        window = config.canary_observation_window_minutes or self.settings.commercial_canary_min_observation_minutes
        metrics = await self.get_canary_metrics(config_id, window_minutes=window)
        canary = metrics["canary"]
        stable = metrics["stable"]

        checks = []
        
        # 1. Min requests
        min_reqs = self.settings.commercial_canary_min_requests_per_step
        checks.append({
            "name": "min_requests",
            "pass": canary["request_count"] >= min_reqs,
            "actual": canary["request_count"],
            "threshold": min_reqs
        })

        # 2. Observation time
        started_at = config.canary_started_at or config.created_at
        observation_mins = (datetime.now(timezone.utc) - started_at).total_seconds() / 60
        checks.append({
            "name": "min_observation_time",
            "pass": observation_mins >= window,
            "actual": round(observation_mins, 1),
            "threshold": window
        })

        # 3. Margin
        min_margin = self.settings.commercial_canary_min_margin_percent
        checks.append({
            "name": "min_margin",
            "pass": canary["avg_margin_percent"] >= min_margin,
            "actual": canary["avg_margin_percent"],
            "threshold": min_margin
        })

        # 4. Error Rate
        max_error = self.settings.commercial_canary_max_error_rate_percent
        checks.append({
            "name": "max_error_rate",
            "pass": canary["error_rate"] <= max_error,
            "actual": canary["error_rate"],
            "threshold": max_error
        })

        # 5. Latency Regression
        if stable.get("avg_latency_ms", 0) > 0:
            regression = ((canary["avg_latency_ms"] - stable["avg_latency_ms"]) / stable["avg_latency_ms"]) * 100
            max_regression = self.settings.commercial_canary_max_latency_regression_percent
            checks.append({
                "name": "latency_regression",
                "pass": regression <= max_regression,
                "actual": round(regression, 2),
                "threshold": max_regression
            })
        else:
             checks.append({
                "name": "latency_regression",
                "pass": True,
                "actual": 0,
                "threshold": self.settings.commercial_canary_max_latency_regression_percent,
                "note": "No stable latency data for comparison"
            })

        # 6. Estimation Error
        max_est_err = self.settings.commercial_canary_max_estimation_error_percent
        checks.append({
            "name": "max_estimation_error",
            "pass": canary["avg_estimation_error_percent"] <= max_est_err,
            "actual": canary["avg_estimation_error_percent"],
            "threshold": max_est_err
        })

        all_pass = all(c["pass"] for c in checks)
        
        return {
            "pass": all_pass,
            "checks": checks,
            "metrics": metrics,
            "config_id": str(config_id)
        }

    async def recommend_next_step(self, config_id: uuid.UUID) -> Dict[str, Any]:
        slo = await self.evaluate_canary_slo(config_id)
        if not slo["pass"]:
            return {"action": "wait", "reason": "SLO not met", "slo": slo}

        config = await self.db.get(CommercialRoutingConfig, config_id)
        steps = [int(s.strip()) for s in self.settings.commercial_canary_promotion_steps.split(",")]
        
        current = config.canary_percent
        try:
            # Find next step
            next_percent = next((s for s in steps if s > current), 100)
            if next_percent < 100:
                return {"action": "promote", "next_percent": next_percent, "slo": slo}
            else:
                return {"action": "complete", "next_percent": 100, "slo": slo}
        except Exception as e:
            return {"action": "error", "reason": str(e), "slo": slo}

    async def promote_canary_step(self, config_id: uuid.UUID, actor: str = "system") -> Dict[str, Any]:
        recommendation = await self.recommend_next_step(config_id)
        
        config = await self.db.get(CommercialRoutingConfig, config_id)
        mode = self.settings.commercial_canary_auto_promotion_mode
        
        if recommendation["action"] == "wait":
            return recommendation

        if mode == "dry_run" and actor == "system":
            return {
                "action": recommendation["action"],
                "would_promote_to": recommendation["next_percent"],
                "mode": "dry_run",
                "slo": recommendation["slo"]
            }
        
        if recommendation["action"] == "promote":
            old_percent = config.canary_percent
            new_percent = recommendation["next_percent"]
            
            config.canary_percent = new_percent
            config.canary_last_promoted_at = datetime.now(timezone.utc)
            config.canary_promotion_status = "observing"
            config.canary_current_step = new_percent
            
            await self._log_action(
                action="canary_step_promoted",
                payload={"config_id": str(config_id), "before": old_percent, "after": new_percent, "metrics": recommendation["slo"]["metrics"]},
                actor=actor
            )
            await self.db.commit()
            return {"action": "promoted", "new_percent": new_percent, "config_id": str(config_id)}

        if recommendation["action"] == "complete":
            return await self.complete_canary_to_stable(config_id, actor=actor)

        return recommendation

    async def complete_canary_to_stable(self, config_id: uuid.UUID, actor: str = "system") -> Dict[str, Any]:
        config = await self.db.get(CommercialRoutingConfig, config_id)
        
        # 1. Deactivate current stable configs for this scope
        await self.db.execute(
            update(CommercialRoutingConfig)
            .where(
                CommercialRoutingConfig.scope_type == config.scope_type,
                CommercialRoutingConfig.provider == config.provider,
                CommercialRoutingConfig.model == config.model,
                CommercialRoutingConfig.is_active == True,
                CommercialRoutingConfig.canary_enabled == False
            )
            .values(is_active=False)
        )
        
        # 2. Promote canary to stable
        config.canary_enabled = False
        config.canary_percent = 0
        config.canary_promotion_status = "completed"
        config.stable_promoted_at = datetime.now(timezone.utc)
        
        await self._log_action(
            action="canary_completed_to_stable",
            payload={"config_id": str(config_id), "scope": config.scope_type},
            actor=actor
        )
        await self.db.commit()
        return {"action": "completed", "config_id": str(config_id)}

    async def auto_rollback_if_unhealthy(self, config_id: uuid.UUID, actor: str = "system") -> Dict[str, Any]:
        if not self.settings.commercial_canary_auto_rollback_enabled:
            return {"action": "skip", "reason": "auto_rollback_disabled"}

        config = await self.db.get(CommercialRoutingConfig, config_id)
        if not config or not config.canary_enabled:
            return {"action": "skip", "reason": "not_canary"}

        window = config.canary_observation_window_minutes or self.settings.commercial_canary_min_observation_minutes
        metrics = await self.get_canary_metrics(config_id, window_minutes=window)
        canary = metrics["canary"]
        
        rollback_needed = False
        reason = ""
        
        # Critical SLO violations trigger rollback
        if canary["error_rate"] > 10.0:
            rollback_needed = True
            reason = f"Critical error rate: {canary['error_rate']}%"
        elif canary["avg_margin_percent"] < 0:
            rollback_needed = True
            reason = f"Negative margin: {canary['avg_margin_percent']}%"
        
        if rollback_needed:
            config.is_active = False
            config.canary_promotion_status = "rolled_back"
            config.canary_failure_reason = reason
            
            await self._log_action(
                action="canary_auto_rollback",
                payload={"config_id": str(config_id), "reason": reason, "metrics": canary},
                actor=actor
            )
            await self.db.commit()
            return {"action": "rolled_back", "reason": reason, "config_id": str(config_id)}
            
        return {"action": "none", "config_id": str(config_id)}

    async def list_active_promotions(self) -> List[Dict[str, Any]]:
        stmt = select(CommercialRoutingConfig).where(
            CommercialRoutingConfig.is_active == True,
            CommercialRoutingConfig.canary_enabled == True
        ).order_by(desc(CommercialRoutingConfig.created_at))
        
        res = await self.db.execute(stmt)
        configs = res.scalars().all()
        
        results = []
        for config in configs:
            slo = await self.evaluate_canary_slo(config.id)
            results.append({
                "id": str(config.id),
                "scope": config.scope_type,
                "provider": config.provider,
                "model": config.model,
                "current_percent": config.canary_percent,
                "status": config.canary_promotion_status,
                "slo_pass": slo["pass"],
                "metrics": slo["metrics"]["canary"]
            })
        return results

    async def _log_action(self, action: str, payload: Dict[str, Any], actor: str):
        log = AdminActionLog(
            action=action,
            admin_role="system" if actor == "system" else "admin",
            payload_json=payload,
            status="success"
        )
        self.db.add(log)
