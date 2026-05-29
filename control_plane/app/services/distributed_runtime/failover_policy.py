import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.runtime.distributed_runtime import DistributedFailoverEvent
from app.core.time import utc_now

class FailoverPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_failover(self, job_id: uuid.UUID, from_node_id: Optional[uuid.UUID], to_node_id: uuid.UUID, reason: str):
        event = DistributedFailoverEvent(
            job_id=job_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            reason=reason
        )
        self.db.add(event)
        await self.db.commit()
        return event