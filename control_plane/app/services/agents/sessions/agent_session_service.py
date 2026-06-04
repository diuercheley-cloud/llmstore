# Owner: agent-platform
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_sessions import (
    AgentSession,
    AgentSessionRun,
    AgentSessionSummary,
)
from app.services.agents.sessions.conversation_thread_service import ConversationThreadService
from app.services.agents.sessions.session_history_policy import SessionHistoryPolicyService
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class SessionNotFoundError(RuntimeError):
    pass


class SessionNotActiveError(RuntimeError):
    pass


class AgentSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.thread_service = ConversationThreadService(db)
        self.policy_service = SessionHistoryPolicyService(db)

    async def create_session(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        retention_policy: Optional[Dict[str, Any]] = None,
    ) -> AgentSession:
        session = AgentSession(
            tenant_id=tenant_id,
            agent_id=agent_id,
            user_id=user_id,
            title=title or f"Session with {agent_id}",
            status="active",
            retention_policy=retention_policy or {"retention_days": 90},
            metadata=metadata or {},
            last_message_at=utc_now(),
        )
        self.db.add(session)
        await self.db.flush()

        thread = await self.thread_service.create_thread(session.id)
        logger.info(
            f"Created session {session.id} for tenant {tenant_id}, agent {agent_id}, thread {thread.id}"
        )
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(
        self, session_id: uuid.UUID, tenant_id: str
    ) -> Optional[AgentSession]:
        stmt = select(AgentSession).where(
            AgentSession.id == session_id,
            AgentSession.tenant_id == tenant_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_sessions(
        self,
        tenant_id: str,
        agent_id: Optional[uuid.UUID] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AgentSession]:
        stmt = select(AgentSession).where(AgentSession.tenant_id == tenant_id)
        if agent_id:
            stmt = stmt.where(AgentSession.agent_id == agent_id)
        if user_id:
            stmt = stmt.where(AgentSession.user_id == user_id)
        if status:
            stmt = stmt.where(AgentSession.status == status)
        stmt = stmt.order_by(AgentSession.last_message_at.desc().nullslast())
        stmt = stmt.offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_session(
        self,
        session_id: uuid.UUID,
        tenant_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentSession]:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return None
        if title is not None:
            session.title = title
        if status is not None:
            session.status = status
        if metadata is not None:
            current = session.session_metadata or {}
            current.update(metadata)
            session.session_metadata = current
        session.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(
        self, session_id: uuid.UUID, tenant_id: str
    ) -> bool:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.commit()
        return True

    async def archive_session(
        self, session_id: uuid.UUID, tenant_id: str
    ) -> Optional[AgentSession]:
        return await self.update_session(session_id, tenant_id, status="archived")

    async def get_or_create_default_session(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        user_id: Optional[str] = None,
    ) -> AgentSession:
        stmt = (
            select(AgentSession)
            .where(
                AgentSession.tenant_id == tenant_id,
                AgentSession.agent_id == agent_id,
                AgentSession.status == "active",
            )
            .order_by(AgentSession.last_message_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            return session
        return await self.create_session(
            tenant_id=tenant_id,
            agent_id=agent_id,
            user_id=user_id,
            title=f"Default session with {agent_id}",
        )

    async def touch_session(
        self, session_id: uuid.UUID
    ) -> None:
        stmt = select(AgentSession).where(AgentSession.id == session_id)
        res = await self.db.execute(stmt)
        session = res.scalar_one_or_none()
        if session:
            session.last_message_at = utc_now()
            await self.db.commit()

    async def link_run_to_session(
        self, session_id: uuid.UUID, run_id: uuid.UUID
    ) -> AgentSessionRun:
        link = AgentSessionRun(
            session_id=session_id,
            run_id=run_id,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_session_runs(
        self, session_id: uuid.UUID, tenant_id: str
    ) -> List[AgentSessionRun]:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        stmt = (
            select(AgentSessionRun)
            .where(AgentSessionRun.session_id == session_id)
            .order_by(AgentSessionRun.created_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def count_active_sessions(
        self, tenant_id: str
    ) -> int:
        stmt = select(func.count(AgentSession.id)).where(
            AgentSession.tenant_id == tenant_id,
            AgentSession.status == "active",
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def apply_retention_policies(
        self, dry_run: bool = False
    ) -> Dict[str, int]:
        return await self.policy_service.apply_retention_policies(self.db, dry_run)

    async def check_and_trigger_summarization(
        self, session_id: uuid.UUID
    ) -> Optional[AgentSessionSummary]:
        if await self.policy_service.should_summarize(session_id):
            logger.info(f"Triggering automatic summarization for session {session_id}")
            context = await self.policy_service.build_summary_context(session_id)
            
            # Here we would normally call an LLM to summarize
            # For now, we'll create a placeholder summary or use a mock logic
            summary_text = f"Automatic summary of the conversation as of {utc_now().isoformat()}"
            
            summary = await self.policy_service.create_summary(
                session_id=session_id,
                summary_text=summary_text,
            )
            
            # Update session cache
            stmt = select(AgentSession).where(AgentSession.id == session_id)
            res = await self.db.execute(stmt)
            session = res.scalar_one_or_none()
            if session:
                session.summary = summary_text
                await self.db.commit()
            
            return summary
        return None
