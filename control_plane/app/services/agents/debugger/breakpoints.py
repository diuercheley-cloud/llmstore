# Owner: agent-platform
import logging
import uuid
from typing import List, Optional

from app.models.agent_debugger import AgentBreakpoint
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class BreakpointManager:
    """
    Manages breakpoints for agent runs.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_breakpoint(self, run_id: uuid.UUID, bp_type: str, target: Optional[str] = None) -> AgentBreakpoint:
        bp = AgentBreakpoint(
            run_id=run_id,
            type=bp_type,
            target=target,
            is_enabled=True
        )
        self.db.add(bp)
        await self.db.flush()
        return bp

    async def get_breakpoints(self, run_id: uuid.UUID) -> List[AgentBreakpoint]:
        stmt = select(AgentBreakpoint).where(
            AgentBreakpoint.run_id == run_id,
            AgentBreakpoint.is_enabled == True
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_breakpoint(self, bp_id: uuid.UUID):
        stmt = select(AgentBreakpoint).where(AgentBreakpoint.id == bp_id)
        res = await self.db.execute(stmt)
        bp = res.scalar_one_or_none()
        if bp:
            await self.db.delete(bp)
            await self.db.flush()

    def should_break(self, active_breakpoints: List[AgentBreakpoint], event_type: str, target: Optional[str] = None) -> bool:
        """
        Checks if the current event matches any active breakpoint.
        """
        for bp in active_breakpoints:
            if bp.type == event_type:
                if bp.target is None or bp.target == target:
                    return True
        return False
