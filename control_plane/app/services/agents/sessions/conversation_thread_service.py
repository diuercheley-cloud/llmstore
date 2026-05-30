# Owner: agent-platform
import uuid
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, List, Optional, Dict
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, delete

from app.core.time import utc_now
from app.models.agent_sessions import (
    AgentConversationThread,
    AgentThreadMessage,
    AgentSession,
)

logger = logging.getLogger(__name__)


class ThreadNotFoundError(RuntimeError):
    pass


class ConversationThreadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_thread(
        self, session_id: uuid.UUID, title: Optional[str] = None
    ) -> AgentConversationThread:
        thread = AgentConversationThread(
            session_id=session_id,
            title=title,
            status="active",
        )
        self.db.add(thread)
        await self.db.flush()
        return thread

    async def get_thread(
        self, thread_id: uuid.UUID
    ) -> Optional[AgentConversationThread]:
        stmt = select(AgentConversationThread).where(
            AgentConversationThread.id == thread_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_default_thread(
        self, session_id: uuid.UUID
    ) -> Optional[AgentConversationThread]:
        stmt = (
            select(AgentConversationThread)
            .where(
                AgentConversationThread.session_id == session_id,
                AgentConversationThread.status == "active",
            )
            .order_by(AgentConversationThread.created_at.asc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        thread_id: Optional[uuid.UUID] = None,
        run_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentThreadMessage:
        if thread_id is None:
            thread = await self.get_default_thread(session_id)
            if not thread:
                thread = await self.create_thread(session_id)
            thread_id = thread.id

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        message = AgentThreadMessage(
            thread_id=thread_id,
            session_id=session_id,
            run_id=run_id,
            role=role,
            content=content,
            content_hash=content_hash,
            metadata=metadata or {},
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
        before_id: Optional[uuid.UUID] = None,
    ) -> List[AgentThreadMessage]:
        stmt = (
            select(AgentThreadMessage)
            .where(AgentThreadMessage.session_id == session_id)
            .order_by(AgentThreadMessage.created_at.asc())
        )
        if before_id:
            before_msg = await self.db.execute(
                select(AgentThreadMessage.created_at).where(
                    AgentThreadMessage.id == before_id
                )
            )
            before_ts = before_msg.scalar_one_or_none()
            if before_ts:
                stmt = stmt.where(AgentThreadMessage.created_at < before_ts)

        stmt = stmt.offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def count_messages(self, session_id: uuid.UUID) -> int:
        stmt = select(func.count(AgentThreadMessage.id)).where(
            AgentThreadMessage.session_id == session_id
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def get_thread_messages(
        self, thread_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> List[AgentThreadMessage]:
        stmt = (
            select(AgentThreadMessage)
            .where(AgentThreadMessage.thread_id == thread_id)
            .order_by(AgentThreadMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_session_messages(self, session_id: uuid.UUID) -> int:
        stmt = delete(AgentThreadMessage).where(
            AgentThreadMessage.session_id == session_id
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount

    async def build_conversation_history(
        self,
        session_id: uuid.UUID,
        max_messages: int = 50,
        include_summary: bool = False,
    ) -> List[Dict[str, Any]]:
        messages = await self.get_messages(session_id, limit=max_messages)
        history = []
        for msg in messages:
            entry = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.metadata:
                entry["metadata"] = msg.metadata
            history.append(entry)
        return history
