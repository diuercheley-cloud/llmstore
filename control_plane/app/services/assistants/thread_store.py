import logging
import uuid
from typing import Any

from app.models.agents.assistants import AssistantThread
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class ThreadStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_thread(
        self,
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> AssistantThread:
        thread = AssistantThread(id=uuid.uuid4(), tenant_id=tenant_id, metadata_json=metadata)
        self.db.add(thread)
        await self.db.flush()
        return thread

    async def get_thread(self, tenant_id: str, thread_id: uuid.UUID) -> AssistantThread | None:
        stmt = select(AssistantThread).where(
            AssistantThread.id == thread_id, AssistantThread.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
