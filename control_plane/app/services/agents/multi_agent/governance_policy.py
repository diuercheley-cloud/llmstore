# Owner: agent-platform
import uuid

from app.models.agents.multi_agent import AgentTeamDelegation, AgentTeamRun
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class MultiAgentPolicyService:
    """
    Enforces production-grade limits for multi-agent systems.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_delegation(self, run_id: uuid.UUID, parent_id: uuid.UUID, child_id: uuid.UUID) -> tuple[bool, str]:
        # 1. Max Depth
        depth = await self._get_delegation_depth(run_id, parent_id)
        if depth >= 5: # Default production limit
            return False, f"Max delegation depth exceeded: {depth+1} > 5"

        # 2. Max Fanout (from parent)
        fanout = await self._get_fanout(run_id, parent_id)
        if fanout >= 10:
            return False, f"Max fanout exceeded for agent {parent_id}: {fanout+1} > 10"

        return True, "OK"

    async def _get_delegation_depth(self, run_id: uuid.UUID, agent_id: uuid.UUID) -> int:
        depth = 0
        curr_id = agent_id
        while curr_id:
            stmt = select(AgentTeamDelegation).where(
                AgentTeamDelegation.run_id == run_id,
                AgentTeamDelegation.child_agent_id == curr_id
            )
            res = await self.db.execute(stmt)
            delegation = res.scalar_one_or_none()
            if not delegation:
                break
            depth += 1
            curr_id = delegation.parent_agent_id
            if depth > 20: # Safety break
                break
        return depth

    async def _get_fanout(self, run_id: uuid.UUID, parent_id: uuid.UUID) -> int:
        stmt = select(func.count(AgentTeamDelegation.id)).where(
            AgentTeamDelegation.run_id == run_id,
            AgentTeamDelegation.parent_agent_id == parent_id
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def check_shared_budget(self, run_id: uuid.UUID, requested_cost: float) -> bool:
        stmt = select(AgentTeamRun).where(AgentTeamRun.id == run_id)
        res = await self.db.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            return False
            
        # shared_budget_brl could be a field in AgentTeamRun or in TeamDefinition
        limit = getattr(run, "shared_budget_brl", 1.0) # Default 1.0 BRL
        current = getattr(run, "total_cost_brl", 0.0)
        
        if current + requested_cost > limit:
            return False
        return True
