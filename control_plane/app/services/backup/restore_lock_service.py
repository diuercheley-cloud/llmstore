import fcntl
import logging
from pathlib import Path

from app.core.config import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MaintenanceMode:
    _active = False

    @classmethod
    def set_active(cls, active: bool):
        cls._active = active
        marker_path = Path("/tmp/maintenance.active")
        try:
            if active:
                marker_path.touch(exist_ok=True)
            else:
                if marker_path.exists():
                    marker_path.unlink()
        except Exception as e:
            logger.error(f"Failed to update maintenance file marker: {e}")

    @classmethod
    def is_active(cls) -> bool:
        if cls._active:
            return True
        if Path("/tmp/maintenance.active").exists():
            return True
        return False


class RestoreLockService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.lock_file_path = (
            Path(self.settings.disaster_recovery_backup_dir or "/tmp") / "restore.lock"
        )
        self._file_handle = None
        self._pg_locked = False

    async def acquire_lock(self) -> bool:
        from app.core.metrics import RESTORE_LOCK_CONTENTION_TOTAL

        url = self.settings.database_url
        if url.startswith("postgresql") or url.startswith("postgres"):
            try:
                result = await self.db.execute(text("SELECT pg_try_advisory_lock(18273918273)"))
                acquired = result.scalar()
                if acquired:
                    self._pg_locked = True
                    MaintenanceMode.set_active(True)
                    return True
                RESTORE_LOCK_CONTENTION_TOTAL.inc()
                return False
            except Exception as e:
                logger.error(
                    f"Failed to acquire PG advisory lock: {e}",
                    extra={"correlation_id": "", "extra_data": {"error": str(e)}},
                )
                RESTORE_LOCK_CONTENTION_TOTAL.inc()
                return False
        else:
            try:
                self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
                self._file_handle = open(self.lock_file_path, "w")
                fcntl.flock(self._file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                MaintenanceMode.set_active(True)
                return True
            except OSError as e:
                logger.warning(
                    f"Failed to acquire local file lock: {e}",
                    extra={"correlation_id": "", "extra_data": {"error": str(e)}},
                )
                RESTORE_LOCK_CONTENTION_TOTAL.inc()
                if self._file_handle:
                    try:
                        self._file_handle.close()
                    except Exception:
                        pass
                    self._file_handle = None
                return False

    async def release_lock(self) -> None:
        try:
            MaintenanceMode.set_active(False)
        except Exception as e:
            logger.error(f"Failed to deactivate maintenance mode: {e}")

        url = self.settings.database_url
        if url.startswith("postgresql") or url.startswith("postgres"):
            if self._pg_locked:
                try:
                    await self.db.execute(text("SELECT pg_advisory_unlock(18273918273)"))
                    await self.db.commit()
                except Exception as e:
                    logger.error(
                        f"Failed to release PG advisory lock: {e}",
                        extra={"correlation_id": "", "extra_data": {"error": str(e)}},
                    )
                finally:
                    self._pg_locked = False
        else:
            if self._file_handle:
                try:
                    fcntl.flock(self._file_handle, fcntl.LOCK_UN)
                    self._file_handle.close()
                except Exception as e:
                    logger.error(
                        f"Failed to release file lock: {e}",
                        extra={"correlation_id": "", "extra_data": {"error": str(e)}},
                    )
                finally:
                    self._file_handle = None
