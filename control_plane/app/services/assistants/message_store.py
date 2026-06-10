import logging
import uuid
from typing import Any, Dict, List, Optional

from app.models.agents.assistants import AssistantMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class MessageStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self,
        thread_id: uuid.UUID,
        role: str,
        content: str,
        assistant_id: Optional[uuid.UUID] = None,
        run_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssistantMessage:
        message = AssistantMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role=role,
            content=content,
            assistant_id=assistant_id,
            run_id=run_id,
            metadata_json=metadata
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def list_messages(self, thread_id: uuid.UUID, limit: int = 100) -> List[AssistantMessage]:
        stmt = select(AssistantMessage).where(
            AssistantMessage.thread_id == thread_id
        ).order_by(AssistantMessage.created_at.asc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
