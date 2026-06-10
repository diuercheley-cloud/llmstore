from enum import Enum
from typing import List, Optional

from app.models.agents.agent_routing import (
    AgentCostQualityProfile,
    AgentModelCapability,
    AgentRoutingPolicy,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PolicyType(str, Enum):
    LOWEST_COST = "lowest_cost"
    BALANCED = "balanced"
    HIGH_QUALITY = "high_quality"
    LOCAL_FIRST = "local_first"
    SOVEREIGN_ONLY = "sovereign_only"
    STRUCTURED_OUTPUT_STRICT = "structured_output_strict"


class CostQualityPolicy:
    """
    Applies cost and quality policies to filter and rank candidate models.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_policy(self, name: str) -> Optional[AgentRoutingPolicy]:
        result = await self.db.execute(select(AgentRoutingPolicy).filter(AgentRoutingPolicy.name == name, AgentRoutingPolicy.is_active == True))
        return result.scalars().first()

    async def get_profile(self, name: str) -> Optional[AgentCostQualityProfile]:
        result = await self.db.execute(select(AgentCostQualityProfile).filter(AgentCostQualityProfile.name == name))
        return result.scalars().first()

    async def apply_policy(
        self,
        models: List[AgentModelCapability],
        policy_name: str,
        profile_name: Optional[str] = None
    ) -> List[AgentModelCapability]:
        policy = await self.get_policy(policy_name)
        profile = await self.get_profile(profile_name) if profile_name else None

        filtered_models = models

        # Apply profile constraints if present
        if profile:
            if profile.max_cost_input is not None:
                filtered_models = [m for m in filtered_models if m.cost_input <= profile.max_cost_input]
            if profile.max_cost_output is not None:
                filtered_models = [m for m in filtered_models if m.cost_output <= profile.max_cost_output]
            filtered_models = [m for m in filtered_models if m.quality_tier >= profile.min_quality_tier]

        # Apply policy logic
        if policy_name == PolicyType.LOWEST_COST:
            return sorted(filtered_models, key=lambda m: (m.cost_input + m.cost_output, -m.quality_tier))
        
        if policy_name == PolicyType.HIGH_QUALITY:
            return sorted(filtered_models, key=lambda m: (-m.quality_tier, m.cost_input + m.cost_output))
        
        if policy_name == PolicyType.BALANCED:
            # Simple balance: quality tier / (cost + 1)
            return sorted(filtered_models, key=lambda m: -(m.quality_tier / (m.cost_input + m.cost_output + 0.0001)))

        if policy_name == PolicyType.SOVEREIGN_ONLY:
            filtered_models = [m for m in filtered_models if m.provider == "local"]
            return sorted(filtered_models, key=lambda m: (-m.quality_tier, m.cost_input + m.cost_output))

        if policy_name == PolicyType.STRUCTURED_OUTPUT_STRICT:
            filtered_models = [m for m in filtered_models if m.supports_json_mode]
            return sorted(filtered_models, key=lambda m: (-m.quality_tier, m.cost_input + m.cost_output))

        return filtered_models
