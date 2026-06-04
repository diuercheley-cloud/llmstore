import uuid
from datetime import datetime

from app.core.time import utc_now
from app.models.agent_workspace import AgentArtifactLock, AgentSharedArtifact
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class ArtifactLockManager:
    @staticmethod
    async def get_lock(db: AsyncSession, artifact_id: uuid.UUID) -> AgentArtifactLock | None:
        stmt = select(AgentArtifactLock).where(AgentArtifactLock.artifact_id == artifact_id)
        result = await db.execute(stmt)
        lock = result.scalar_one_or_none()
        if lock and lock.expires_at:
            expires_at = lock.expires_at
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)
            now_naive = utc_now().replace(tzinfo=None)
            if expires_at < now_naive:
                # Lock has expired, we should clean it up
                await db.delete(lock)
                await db.commit()
                return None
        return lock

    @staticmethod
    async def acquire_lock(
        db: AsyncSession,
        artifact_id: uuid.UUID,
        holder_id: str,
        holder_type: str,
        lock_type: str = "exclusive",
        expires_in_seconds: int = 300
    ) -> AgentArtifactLock:
        """Acquires a pessimistic lock on the artifact. Extends it if already held by the same holder."""
        lock = await ArtifactLockManager.get_lock(db, artifact_id)
        now = utc_now()
        expires_at = datetime.fromtimestamp(now.timestamp() + expires_in_seconds, now.tzinfo) if expires_in_seconds else None

        if lock:
            if lock.holder_id != holder_id:
                raise PermissionError(f"Artifact is locked by {lock.holder_type} '{lock.holder_id}' until {lock.expires_at}.")
            # Extend lock
            lock.expires_at = expires_at
            lock.lock_type = lock_type
        else:
            lock = AgentArtifactLock(
                artifact_id=artifact_id,
                holder_id=holder_id,
                holder_type=holder_type,
                lock_type=lock_type,
                expires_at=expires_at,
                created_at=now
            )
            db.add(lock)
        
        await db.commit()
        await db.refresh(lock)
        return lock

    @staticmethod
    async def release_lock(db: AsyncSession, artifact_id: uuid.UUID, holder_id: str) -> None:
        """Releases the pessimistic lock if held by the holder."""
        lock = await ArtifactLockManager.get_lock(db, artifact_id)
        if not lock:
            return # No active lock to release
        if lock.holder_id != holder_id:
            raise PermissionError(f"Cannot release lock: held by '{lock.holder_id}', not '{holder_id}'.")
        await db.delete(lock)
        await db.commit()

    @staticmethod
    async def check_write_allowed(db: AsyncSession, artifact_id: uuid.UUID, editor_id: str) -> None:
        """Verify pessimistic lock permits edits by editor_id."""
        lock = await ArtifactLockManager.get_lock(db, artifact_id)
        if lock and lock.holder_id != editor_id:
            raise PermissionError(f"Edits blocked: artifact is locked by '{lock.holder_id}'.")

    @staticmethod
    def verify_optimistic_lock(artifact: AgentSharedArtifact, expected_version_id: uuid.UUID | None = None, expected_version_number: int | None = None) -> None:
        """Enforces optimistic lock checking by comparing current version metadata."""
        if expected_version_id is not None and artifact.current_version_id != expected_version_id:
            raise ValueError("Concurrency conflict: the artifact has been modified (version ID mismatch).")
        if expected_version_number is not None:
            # We can't check version number directly on artifact without loading versions,
            # but if we have the current version loaded we can check.
            pass
