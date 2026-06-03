from __future__ import annotations

import logging
import uuid
from typing import Any, cast
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.services.billing.revenue_protection import get_active_revenue_protection_constraints
from app.models.commercial_qos_tier import CommercialQoSTier
from app.models.client import Client
from app.schemas.routing import (
    CommercialScoreExplained,
    TaskType,
)

logger = logging.getLogger(__name__)

class CommercialQoSService:
    @staticmethod
    async def get_all_tiers(db: AsyncSession) -> list[CommercialQoSTier]:
        result = await db.execute(select(CommercialQoSTier).order_by(CommercialQoSTier.priority.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_tier_by_name(db: AsyncSession, name: str) -> CommercialQoSTier | None:
        result = await db.execute(select(CommercialQoSTier).where(CommercialQoSTier.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def resolve_qos_tier(db: AsyncSession, client_id: uuid.UUID | None, plan_code: str | None) -> CommercialQoSTier:
        # Default fallback is 'Basic'
        default_tier_name = "Basic"
        
        if client_id:
            result = await db.execute(
                select(Client).options(selectinload(Client.billing_plan)).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()
            if client and client.billing_plan:
                plan_code = client.billing_plan.code

        tier_mapping = {
            "free": "Free",
            "basic": "Basic",
            "pro": "Pro",
            "premium": "Premium",
            "enterprise": "Enterprise",
            "enterprise-local": "Enterprise",
        }
        
        tier_name = tier_mapping.get(plan_code or "", default_tier_name)
        tier = await CommercialQoSService.get_tier_by_name(db, tier_name)
        
        if not tier:
            # Try to get any enabled tier if specific one not found
            result = await db.execute(select(CommercialQoSTier).where(CommercialQoSTier.enabled == True).limit(1))
            tier = result.scalar_one_or_none()
            
        if not tier:
            # Absolute fallback (should not happen after seeding)
            return CommercialQoSTier(
                name="Fallback-Basic",
                enabled=True,
                priority=10,
                target_latency_ms=1000,
                max_p95_latency_ms=3000,
                min_margin_percent=5.0,
                allow_cloud=False,
                degradation_policy="best_effort"
            )
        constraints = get_active_revenue_protection_constraints(client_id=client_id, qos_tier=tier.name)
        if constraints.get("qos_priority_override") == "reduced":
            tier.priority = max(1, int(tier.priority) - 5)
            tier.queue_priority = max(1, int(tier.queue_priority) - 10)
        return tier

    @staticmethod
    def evaluate_route_against_qos(
        tier: CommercialQoSTier,
        candidate: dict[str, Any],
        estimated_margin_percent: float | None,
        estimated_cost_brl: float,
        is_cloud: bool,
        current_p95_latency: int | None = None
    ) -> tuple[bool, list[str]]:
        reasons = []
        
        # 1. Cloud allowance
        if is_cloud and not tier.allow_cloud:
            reasons.append("cloud_not_allowed_for_tier")
            
        # 2. Margin constraint
        if is_cloud and estimated_margin_percent is not None:
            min_margin = float(tier.min_margin_percent) if tier.min_margin_percent is not None else 0.0
            if estimated_margin_percent < min_margin:
                reasons.append(f"margin_{estimated_margin_percent:.2f}_below_min_{min_margin}")
                
        # 3. Cost constraint
        max_cost = float(tier.max_cost_per_request_brl) if tier.max_cost_per_request_brl is not None else 999.0
        if estimated_cost_brl > max_cost:
            reasons.append(f"cost_{estimated_cost_brl:.4f}_above_max_{max_cost}")
            
        # 4. Latency p95 constraint
        if current_p95_latency is not None and current_p95_latency > tier.max_p95_latency_ms:
            reasons.append(f"latency_p95_{current_p95_latency}_above_max_{tier.max_p95_latency_ms}")

        # 5. Quality floor
        quality = candidate.get("quality", 50)
        if tier.quality_floor is not None and quality < tier.quality_floor:
            reasons.append(f"quality_{quality}_below_floor_{tier.quality_floor}")

        return len(reasons) == 0, reasons

    @staticmethod
    def choose_degradation_path(
        tier: CommercialQoSTier,
        candidates: list[CommercialScoreExplained],
        rejected: list[CommercialScoreExplained]
    ) -> tuple[CommercialScoreExplained | None, str]:
        policy = tier.degradation_policy
        
        if policy == "block":
            return None, "blocked_by_policy"
            
        if policy == "fallback_local":
            local_candidates = [c for c in candidates if not getattr(c, 'is_cloud', False)]
            if local_candidates:
                return local_candidates[0], "fallback_to_local"
            # If no local in candidates, check rejected
            local_rejected = [c for c in rejected if not getattr(c, 'is_cloud', False)]
            if local_rejected:
                return local_rejected[0], "fallback_to_local_rejected"
                
        if policy == "cheapest":
            all_cands = candidates + rejected
            if all_cands:
                cheapest = min(all_cands, key=lambda x: x.estimated_cost_brl or 999)
                return cheapest, "fallback_to_cheapest"
                
        if policy == "best_effort":
            if candidates:
                return candidates[0], "best_effort_primary"
            if rejected:
                # Pick the "least bad" rejected? For now just pick first
                return rejected[0], "best_effort_fallback"
                
        return None, "no_degradation_path_available"
