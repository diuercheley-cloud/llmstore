import uuid

from app.models.runtime.distributed_runtime import DistributedFailoverEvent
from sqlalchemy.ext.asyncio import AsyncSession


class FailoverPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_failover(
        self, job_id: uuid.UUID, from_node_id: uuid.UUID | None, to_node_id: uuid.UUID, reason: str
    ):
        event = DistributedFailoverEvent(
            job_id=job_id, from_node_id=from_node_id, to_node_id=to_node_id, reason=reason
        )
        self.db.add(event)
        await self.db.commit()
        return event
