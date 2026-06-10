# Owner: agent-platform
import logging
import uuid

from app.models.agents.multi_agent import AgentTeamDelegation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class LoopGuard:
    """
    Prevents infinite cycles in agent delegations.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_cycle(self, run_id: uuid.UUID, parent_id: uuid.UUID, child_id: uuid.UUID) -> bool:
        """
        Simple cycle detection: if child has already delegated back to parent in this run.
        """
        stmt = select(AgentTeamDelegation).where(
            AgentTeamDelegation.run_id == run_id,
            AgentTeamDelegation.parent_agent_id == child_id,
            AgentTeamDelegation.child_agent_id == parent_id
        )
        res = await self.db.execute(stmt)
        if res.scalar_one_or_none():
            logger.warning(f"Cycle detected: {child_id} -> {parent_id}")
            return True
            
        return False
