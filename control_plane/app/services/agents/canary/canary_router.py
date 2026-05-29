# Owner: agent-platform
import uuid
import random
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.agent_canary import AgentCanaryAssignment
from app.core.config import get_settings

class CanaryRouter:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_assignment(self, base_agent_id: uuid.UUID, tenant_id: str) -> Optional[AgentCanaryAssignment]:
        """
        Retrieves an active canary assignment for the given agent and tenant.
        """
        stmt = select(AgentCanaryAssignment).where(
            AgentCanaryAssignment.base_agent_id == base_agent_id,
            AgentCanaryAssignment.tenant_id == tenant_id,
            AgentCanaryAssignment.status == "active"
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def should_trigger_canary(self, assignment: AgentCanaryAssignment) -> bool:
        """
        Determines if a canary/shadow run should be triggered based on traffic percentage.
        """
        if not self.settings.agent_canary_agents_enabled:
            return False
            
        if assignment.is_shadow:
            return True # Shadow runs usually run for 100% of sampled traffic
            
        return random.random() * 100 < assignment.traffic_percentage
