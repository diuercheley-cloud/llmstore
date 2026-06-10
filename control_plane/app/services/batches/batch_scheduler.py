import logging
import uuid

from app.core.time import utc_now
from app.models.core.batches import BatchJob, BatchJobItem
from app.services.agents.agent_runtime import start_run
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class BatchScheduler:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def schedule_batch(self, batch_id: uuid.UUID):
        stmt = select(BatchJob).where(BatchJob.id == batch_id)
        res = await self.db.execute(stmt)
        batch = res.scalar_one_or_none()
        if not batch:
            return

        batch.status = "in_progress"
        await self.db.flush()

        stmt = select(BatchJobItem).where(BatchJobItem.batch_id == batch_id)
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        # In a real system, this would be a background task per item or a separate queue.
        # For simplicity, we trigger them and link AgentRuns.
        for item in items:
            try:
                # Basic mapping: input_data must contain what start_run needs
                # e.g., {"agent_id": "...", "input_text": "..."}
                agent_id = item.input_data.get("agent_id")
                input_text = item.input_data.get("input_text")
                
                if not agent_id or not input_text:
                    item.status = "failed"
                    item.error = "Missing agent_id or input_text in item data"
                    batch.failed_items += 1
                    continue

                run = await start_run(
                    db=self.db,
                    agent_id=uuid.UUID(agent_id),
                    tenant_id=batch.tenant_id,
                    input_text=input_text,
                    correlation_id=str(batch_id)
                )
                
                item.agent_run_id = run.id
                item.status = "in_progress"
                
            except Exception as e:
                logger.exception(f"Failed to schedule item {item.id}")
                item.status = "failed"
                item.error = str(e)
                batch.failed_items += 1

        await self.db.flush()

    async def cancel_batch(self, tenant_id: str, batch_id: uuid.UUID):
        stmt = select(BatchJob).where(
            BatchJob.id == batch_id,
            BatchJob.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        batch = res.scalar_one_or_none()
        if batch and batch.status in ["validating", "in_progress"]:
            batch.status = "cancelled"
            batch.completed_at = utc_now()
            await self.db.flush()
            return True
        return False
