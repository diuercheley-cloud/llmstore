import logging
import uuid
from typing import Any, Dict, Optional

from app.models.assistants import AssistantThread
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class ThreadStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_thread(
        self,
        tenant_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AssistantThread:
        thread = AssistantThread(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            metadata_json=metadata
        )
        self.db.add(thread)
        await self.db.flush()
        return thread

    async def get_thread(self, tenant_id: str, thread_id: uuid.UUID) -> Optional[AssistantThread]:
        stmt = select(AssistantThread).where(
            AssistantThread.id == thread_id,
            AssistantThread.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
