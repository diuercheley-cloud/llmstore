from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_routing_config import CommercialRoutingConfig
from app.models.core.admin_action_log import AdminActionLog
from sqlalchemy import and_, desc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CommercialConfigStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_effective_config(
        self,
        provider: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Gets the effective configuration based on specificity precedence:
        provider_model > model > provider > global > env default
        Also handles canary selection if enabled.
        """
        # Specificity order:
        # 1. provider_model (scope_type='provider_model', provider=P, model=M)
        # 2. model (scope_type='model', model=M)
        # 3. provider (scope_type='provider', provider=P)
        # 4. global (scope_type='global')

        clauses = [
            and_(
                CommercialRoutingConfig.scope_type == "provider_model",
                CommercialRoutingConfig.provider == provider,
                CommercialRoutingConfig.model == model,
            ),
            and_(
                CommercialRoutingConfig.scope_type == "model",
                CommercialRoutingConfig.model == model,
            ),
            and_(
                CommercialRoutingConfig.scope_type == "provider",
                CommercialRoutingConfig.provider == provider,
            ),
            CommercialRoutingConfig.scope_type == "global",
        ]

        # Filter out clauses that have None if they require a value
        active_clauses = []
        if provider and model:
            active_clauses.append(clauses[0])
        if model:
            active_clauses.append(clauses[1])
        if provider:
            active_clauses.append(clauses[2])
        active_clauses.append(clauses[3])

        import sqlalchemy as sa
        from app.services.routing.commercial_auto_apply import CommercialAutoApplyService

        stmt = (
            select(CommercialRoutingConfig)
            .where(and_(CommercialRoutingConfig.is_active == True, or_(*active_clauses)))
            .order_by(
                # Order by specificity
                sa.case(
                    (CommercialRoutingConfig.scope_type == "provider_model", 1),
                    (CommercialRoutingConfig.scope_type == "model", 2),
                    (CommercialRoutingConfig.scope_type == "provider", 3),
                    (CommercialRoutingConfig.scope_type == "global", 4),
                    else_=5,
                ),
                # Order by canary vs stable: we want to consider both
                desc(CommercialRoutingConfig.canary_enabled),
                desc(CommercialRoutingConfig.created_at),
            )
        )

        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        if not configs:
            # Fallback to env defaults
            settings = get_settings()
            return {
                "cost_multiplier": 1.0,
                "margin_weight": settings.commercial_margin_weight,
                "latency_weight": settings.commercial_latency_weight,
                "quality_weight": settings.commercial_quality_weight,
                "local_route_bonus": settings.commercial_local_route_bonus,
                "min_margin_percent": settings.commercial_min_margin_percent,
                "source": "default",
                "config_id": None,
            }

        # Handle canary selection
        selected_config = configs[0]  # Default to most specific

        # If the most specific stable config has a more specific canary, OR
        # if the most specific config IS a canary, evaluate bucket.

        # Let's find the best stable and best canary for the exact same scope
        # specificity matches.

        canary_config = next((c for c in configs if c.canary_enabled), None)
        stable_config = next((c for c in configs if not c.canary_enabled), None)

        if canary_config:
            # Check if bucket matches
            bucket = CommercialAutoApplyService.get_canary_bucket(
                request_id, correlation_id, client_id
            )
            if bucket < canary_config.canary_percent:
                selected_config = canary_config
            else:
                # If bucket doesn't match, we MUST use a stable config if available
                if stable_config:
                    selected_config = stable_config
                else:
                    # No stable config for this scope? Fall back to next specificity or env
                    # This shouldn't really happen with auto-apply as it keeps stable,
                    # but for manual canary-only it might.
                    pass

        return {
            "cost_multiplier": selected_config.cost_multiplier,
            "margin_weight": selected_config.margin_weight,
            "latency_weight": selected_config.latency_weight,
            "quality_weight": selected_config.quality_weight,
            "local_route_bonus": selected_config.local_route_bonus,
            "min_margin_percent": selected_config.min_margin_percent,
            "source": selected_config.source,
            "config_id": str(selected_config.id),
            "is_canary": selected_config.canary_enabled,
        }

    async def list_canaries(self) -> list[CommercialRoutingConfig]:
        stmt = (
            select(CommercialRoutingConfig)
            .where(
                and_(
                    CommercialRoutingConfig.is_active == True,
                    CommercialRoutingConfig.canary_enabled == True,
                )
            )
            .order_by(desc(CommercialRoutingConfig.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def apply_config(
        self,
        scope_type: str,
        provider: str | None = None,
        model: str | None = None,
        cost_multiplier: float = 1.0,
        margin_weight: float = 0.6,
        latency_weight: float = 0.2,
        quality_weight: float = 0.2,
        local_route_bonus: float = 20.0,
        min_margin_percent: float = 10.0,
        source: str = "manual",
        created_by: str | None = None,
        notes: str | None = None,
        force: bool = False,
    ) -> CommercialRoutingConfig:
        """
        Applies a new configuration, deactivating the previous one for the same scope.
        """
        # Validation
        self.validate_config_safety(
            cost_multiplier,
            margin_weight,
            latency_weight,
            quality_weight,
            min_margin_percent,
            force=force,
        )

        # Deactivate existing active configs for the same scope
        update_stmt = (
            update(CommercialRoutingConfig)
            .where(
                and_(
                    CommercialRoutingConfig.scope_type == scope_type,
                    CommercialRoutingConfig.provider == provider,
                    CommercialRoutingConfig.model == model,
                    CommercialRoutingConfig.is_active == True,
                )
            )
            .values(is_active=False, updated_at=datetime.now(UTC))
        )
        await self.db.execute(update_stmt)

        # Create new config
        new_config = CommercialRoutingConfig(
            scope_type=scope_type,
            provider=provider,
            model=model,
            cost_multiplier=cost_multiplier,
            margin_weight=margin_weight,
            latency_weight=latency_weight,
            quality_weight=quality_weight,
            local_route_bonus=local_route_bonus,
            min_margin_percent=min_margin_percent,
            source=source,
            is_active=True,
            created_by=created_by,
            notes=notes,
        )
        self.db.add(new_config)
        await self.db.flush()

        # Audit log
        audit = AdminActionLog(
            action="apply_commercial_config",
            admin_role="admin",
            status="success",
            payload_json={
                "scope": scope_type,
                "provider": provider,
                "model": model,
                "cost_multiplier": cost_multiplier,
                "source": source,
                "notes": notes,
                "config_id": str(new_config.id),
            },
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(new_config)
        return new_config

    def validate_config_safety(
        self,
        cost_multiplier: float,
        margin_weight: float,
        latency_weight: float,
        quality_weight: float,
        min_margin_percent: float,
        force: bool = False,
    ):
        settings = get_settings()

        # Cost multiplier limits
        if not force:
            if cost_multiplier > 3.0 or cost_multiplier < 0.3:
                raise ValueError(
                    f"Cost multiplier {cost_multiplier} out of safe bounds (0.3-3.0). Use force=True to override."
                )

        # Weights sum approx 1.0
        weight_sum = margin_weight + latency_weight + quality_weight
        if abs(weight_sum - 1.0) > 0.01:
            # We could normalize here, but let's be strict for manual apply
            raise ValueError(f"Weights must sum to 1.0 (got {weight_sum:.2f})")

        if min_margin_percent < 0 and not force:
            raise ValueError("Minimum margin percent cannot be negative.")

    async def deactivate_config(self, config_id: uuid.UUID, actor: str = "system") -> bool:
        stmt = select(CommercialRoutingConfig).where(CommercialRoutingConfig.id == config_id)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config or not config.is_active:
            return False

        config.is_active = False
        config.updated_at = datetime.now(UTC)

        audit = AdminActionLog(
            action="deactivate_commercial_config",
            admin_role="admin",
            status="success",
            payload_json={
                "config_id": str(config.id),
                "scope": config.scope_type,
                "provider": config.provider,
                "model": config.model,
            },
        )
        self.db.add(audit)
        await self.db.commit()
        return True

    async def rollback_config(
        self, scope_type: str, provider: str | None, model: str | None, actor: str = "system"
    ) -> CommercialRoutingConfig | None:
        """
        Deactivates current and reactivates the previous one for the same scope.
        """
        # 1. Find and deactivate current
        current_stmt = select(CommercialRoutingConfig).where(
            and_(
                CommercialRoutingConfig.scope_type == scope_type,
                CommercialRoutingConfig.provider == provider,
                CommercialRoutingConfig.model == model,
                CommercialRoutingConfig.is_active == True,
            )
        )
        res = await self.db.execute(current_stmt)
        current = res.scalar_one_or_none()

        if current:
            current.is_active = False
            current.updated_at = datetime.now(UTC)

        # 2. Find previous (most recent inactive, excluding current if it was just deactivated)
        prev_filters = [
            CommercialRoutingConfig.scope_type == scope_type,
            CommercialRoutingConfig.provider == provider,
            CommercialRoutingConfig.model == model,
            CommercialRoutingConfig.is_active == False,
        ]
        if current:
            prev_filters.append(CommercialRoutingConfig.id != current.id)

        prev_stmt = (
            select(CommercialRoutingConfig)
            .where(and_(*prev_filters))
            .order_by(desc(CommercialRoutingConfig.created_at))
            .limit(1)
        )
        res = await self.db.execute(prev_stmt)
        previous = res.scalar_one_or_none()

        if previous:
            previous.is_active = True
            previous.updated_at = datetime.now(UTC)

            audit = AdminActionLog(
                action="rollback_commercial_config",
                admin_role="admin",
                status="success",
                payload_json={
                    "config_id": str(previous.id),
                    "scope": scope_type,
                    "provider": provider,
                    "model": model,
                    "rolled_back_from": str(current.id) if current else None,
                },
            )
            self.db.add(audit)
            await self.db.commit()
            await self.db.refresh(previous)
            return previous

        await self.db.commit()
        return None

    async def list_configs(self, active_only: bool = True) -> list[CommercialRoutingConfig]:
        stmt = select(CommercialRoutingConfig)
        if active_only:
            stmt = stmt.where(CommercialRoutingConfig.is_active == True)
        stmt = stmt.order_by(desc(CommercialRoutingConfig.created_at))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
