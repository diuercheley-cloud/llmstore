import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.time import utc_now
from app.models.batches import BatchJob, BatchJobItem
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class BatchRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_batch(
        self,
        tenant_id: str,
        input_data: List[Dict[str, Any]],
        budget_limit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchJob:
        batch = BatchJob(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            status="validating",
            total_items=len(input_data),
            budget_limit=budget_limit,
            metadata_json=metadata
        )
        self.db.add(batch)
        
        for item_data in input_data:
            item = BatchJobItem(
                id=uuid.uuid4(),
                batch_id=batch.id,
                custom_id=item_data.get("custom_id"),
                input_data=item_data,
                status="pending"
            )
            self.db.add(item)
            
        await self.db.flush()
        return batch

    async def get_batch(self, tenant_id: str, batch_id: uuid.UUID) -> Optional[BatchJob]:
        stmt = select(BatchJob).where(
            BatchJob.id == batch_id,
            BatchJob.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_batches(self, tenant_id: str, limit: int = 20) -> List[BatchJob]:
        stmt = select(BatchJob).where(
            BatchJob.tenant_id == tenant_id
        ).order_by(BatchJob.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_batch_status(self, batch_id: uuid.UUID, status: str):
        stmt = select(BatchJob).where(BatchJob.id == batch_id)
        res = await self.db.execute(stmt)
        batch = res.scalar_one_or_none()
        if batch:
            batch.status = status
            if status in ["completed", "failed", "cancelled"]:
                batch.completed_at = utc_now()
            await self.db.flush()
