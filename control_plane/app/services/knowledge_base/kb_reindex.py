# Owner: agent-platform
import logging
import uuid

from app.models.knowledge_base import (
    KBIngestionJob,
    KnowledgeBase,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class KBReindexService:
    """
    Facilitates full reindexing of a Knowledge Base.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def trigger_reindex(self, kb_id: uuid.UUID) -> KBIngestionJob:
        """
        Starts a background job to re-chunk and re-embed all documents in a KB.
        """
        kb = await self.db.get(KnowledgeBase, kb_id)
        if not kb:
            raise ValueError("KB not found")

        job = KBIngestionJob(
            kb_id=kb_id,
            tenant_id=kb.tenant_id,
            status="running"
        )
        self.db.add(job)
        await self.db.flush()
        
        # In a real system, this would trigger a background task (Celery/Temporal)
        logger.info(f"Reindexing triggered for KB {kb_id}")
        
        # Mock completion
        job.status = "completed"
        job.progress = 1.0
        
        await self.db.commit()
        return job
