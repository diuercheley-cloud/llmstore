# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict

from app.models.agents.agent_debugger import AgentDebugSession, AgentDebugStepEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class DebugSessionManager:
    """
    Manages interactive debug sessions for agent runs.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(self, run_id: uuid.UUID, tenant_id: str) -> AgentDebugSession:
        stmt = select(AgentDebugSession).where(AgentDebugSession.run_id == run_id)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        
        if not session:
            session = AgentDebugSession(
                run_id=run_id,
                tenant_id=tenant_id,
                status="active"
            )
            self.db.add(session)
            await self.db.flush()
        
        return session

    async def pause_session(self, session_id: uuid.UUID):
        stmt = select(AgentDebugSession).where(AgentDebugSession.id == session_id)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            session.status = "paused"
            await self.db.flush()

    async def resume_session(self, session_id: uuid.UUID):
        stmt = select(AgentDebugSession).where(AgentDebugSession.id == session_id)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            session.status = "active"
            await self.db.flush()

    async def record_step_event(self, session_id: uuid.UUID, step_number: int, event_type: str, state: Dict[str, Any], metadata: Dict[str, Any] = None):
        event = AgentDebugStepEvent(
            session_id=session_id,
            step_number=step_number,
            event_type=event_type,
            state_snapshot=state,
            metadata_json=metadata or {}
        )
        self.db.add(event)
        
        # Update current step in session
        stmt = select(AgentDebugSession).where(AgentDebugSession.id == session_id)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            session.current_step = step_number
            
        await self.db.flush()
