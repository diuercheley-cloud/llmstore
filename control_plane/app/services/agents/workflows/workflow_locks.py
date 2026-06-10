# Owner: agent-platform
import logging
import uuid
from datetime import timedelta

from app.core.time import utc_now
from app.models.agents.agent_workflows import AgentWorkflowLock
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class WorkflowLockManager:
    """
    Implements distributed locking using the database.
    Ensures that a workflow run is only processed by one worker at a time.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def acquire_lock(self, lock_key: str, owner_id: uuid.UUID, ttl_seconds: int = 60) -> bool:
        """
        Attempts to acquire a lock for a given key.
        """
        now = utc_now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        
        # 1. Check if lock exists and is valid
        stmt = select(AgentWorkflowLock).where(AgentWorkflowLock.lock_key == lock_key)
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        
        if existing:
            # Handle naive vs aware comparison
            existing_expires = existing.expires_at
            if existing_expires.tzinfo is None and now.tzinfo is not None:
                existing_expires = existing_expires.replace(tzinfo=now.tzinfo)
            elif existing_expires.tzinfo is not None and now.tzinfo is None:
                now = now.replace(tzinfo=existing_expires.tzinfo)

            if existing_expires > now:
                # Lock is still valid and held by someone else
                if existing.owner_id == owner_id:
                    # Already owned by us, extend it
                    existing.expires_at = expires_at
                    await self.db.commit()
                    return True
                return False
            else:
                # Lock expired, remove it
                await self.db.delete(existing)
                await self.db.flush()
        
        # 2. Try to create new lock
        new_lock = AgentWorkflowLock(
            lock_key=lock_key,
            owner_id=owner_id,
            expires_at=expires_at,
            created_at=now
        )
        self.db.add(new_lock)
        try:
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def release_lock(self, lock_key: str, owner_id: uuid.UUID):
        """
        Releases the lock if owned by the caller.
        """
        stmt = delete(AgentWorkflowLock).where(
            AgentWorkflowLock.lock_key == lock_key,
            AgentWorkflowLock.owner_id == owner_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def cleanup_expired_locks(self):
        """
        Removes all expired locks.
        """
        stmt = delete(AgentWorkflowLock).where(AgentWorkflowLock.expires_at <= utc_now())
        await self.db.execute(stmt)
        await self.db.commit()
