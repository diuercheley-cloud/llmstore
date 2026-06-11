import logging
from sqlalchemy.ext.asyncio import AsyncSession
from .errors import RestoreRollbackError

logger = logging.getLogger(__name__)

class RestoreRollbackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def perform_rollback(self, safety_backup_id: str) -> None:
        """
        Performs automatic rollback using a safety backup.
        """
        try:
            from .backup_service import BackupService
            service = BackupService(self.db)
            # We use the internal restore logic that doesn't re-acquire locks
            # if we are already inside a restore flow
            await service._restore_backup_without_lock(safety_backup_id)
            logger.info(f"Automatic rollback to safety backup {safety_backup_id} succeeded.")
        except Exception as e:
            logger.error(f"Automatic rollback to safety backup {safety_backup_id} failed: {e}")
            raise RestoreRollbackError(f"Rollback failed: {e}")
