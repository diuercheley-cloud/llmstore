import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.runtime.distributed_runtime import DistributedJobLease
from app.core.time import utc_now

class DistributedLeaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def acquire_lease(self, job_id: uuid.UUID, node_id: uuid.UUID, duration_seconds: int = 60) -> bool:
        result = await self.db.execute(select(DistributedJobLease).where(DistributedJobLease.job_id == job_id))
        lease = result.scalars().first()
        
        now = utc_now()
        expires_at = now + timedelta(seconds=duration_seconds)
        
        if lease:
            lease_expires_at = lease.expires_at
            if lease_expires_at.tzinfo is None:
                from datetime import timezone
                lease_expires_at = lease_expires_at.replace(tzinfo=timezone.utc)
            if lease.is_active and lease_expires_at > now:
                return False  # Already leased by someone else
            else:
                lease.node_id = node_id
                lease.acquired_at = now
                lease.expires_at = expires_at
                lease.is_active = True
        else:
            lease = DistributedJobLease(job_id=job_id, node_id=node_id, expires_at=expires_at)
            self.db.add(lease)
            
        await self.db.commit()
        return True
        
    async def release_lease(self, job_id: uuid.UUID):
        await self.db.execute(delete(DistributedJobLease).where(DistributedJobLease.job_id == job_id))
        await self.db.commit()