from typing import List, Optional

from app.models.agent_routing import AgentModelCapability
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ModelCapabilityRegistry:
    """
    Registry for model capabilities, costs, and quality tiers.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_capabilities(self, model_id: str) -> Optional[AgentModelCapability]:
        result = await self.db.execute(select(AgentModelCapability).filter(AgentModelCapability.model_id == model_id))
        return result.scalars().first()

    async def list_all_capabilities(self) -> List[AgentModelCapability]:
        result = await self.db.execute(select(AgentModelCapability))
        return list(result.scalars().all())

    async def find_suitable_models(
        self,
        step_class: str,
        min_quality_tier: int = 1,
        requires_tool_calling: bool = False,
        requires_json_mode: bool = False,
        max_cost_input: Optional[float] = None,
        max_cost_output: Optional[float] = None,
    ) -> List[AgentModelCapability]:
        stmt = select(AgentModelCapability).filter(
            AgentModelCapability.quality_tier >= min_quality_tier
        )

        if requires_tool_calling:
            stmt = stmt.filter(AgentModelCapability.supports_tool_calling == True)
        
        if requires_json_mode:
            stmt = stmt.filter(AgentModelCapability.supports_json_mode == True)

        if max_cost_input is not None:
            stmt = stmt.filter(AgentModelCapability.cost_input <= max_cost_input)
        
        if max_cost_output is not None:
            stmt = stmt.filter(AgentModelCapability.cost_output <= max_cost_output)

        result = await self.db.execute(stmt)
        models = list(result.scalars().all())
        
        # Sort by quality tier (desc) then by cost (asc)
        return sorted(
            models,
            key=lambda m: (-m.quality_tier, m.cost_input + m.cost_output)
        )

    async def register_model(self, capability: AgentModelCapability):
        await self.db.merge(capability)
        await self.db.commit()
