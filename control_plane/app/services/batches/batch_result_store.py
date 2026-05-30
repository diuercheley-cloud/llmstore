import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.batches import BatchJob, BatchJobItem

logger = logging.getLogger(__name__)

class BatchResultStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_results(self, tenant_id: str, batch_id: uuid.UUID) -> List[Dict[str, Any]]:
        # Verify ownership
        stmt = select(BatchJob).where(
            BatchJob.id == batch_id,
            BatchJob.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        batch = res.scalar_one_or_none()
        if not batch:
            return []

        stmt = select(BatchJobItem).where(BatchJobItem.batch_id == batch_id)
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        results = []
        for item in items:
            results.append({
                "custom_id": item.custom_id,
                "status": item.status,
                "output": item.output_data,
                "error": item.error,
                "agent_run_id": str(item.agent_run_id) if item.agent_run_id else None
            })
        return results

    async def generate_result_artifact(self, tenant_id: str, batch_id: uuid.UUID) -> str:
        """
        Simulates generation of a JSONL result artifact.
        """
        results = await self.get_results(tenant_id, batch_id)
        jsonl_content = "\n".join([json.dumps(r) for r in results])
        
        # In a real system, we would upload to S3/Storage and return a file_id
        artifact_id = f"batch_res_{batch_id}.jsonl"
        logger.info(f"Generated result artifact {artifact_id} for batch {batch_id}")
        return artifact_id
