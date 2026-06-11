import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from .errors import RestorePromotionError
from app.services.backup.database_providers import SQLiteBackupProvider

logger = logging.getLogger(__name__)

class RestorePromotionService:
    def __init__(self, db: AsyncSession, repo_root: Path):
        self.db = db
        self.repo_root = repo_root

    async def promote_database(self, manifest_scope: str, parts: Dict[str, Any], sqlite_staging_file: Path | None, provider_factory) -> None:
        try:
            db_url = str(self.db.bind.url) if getattr(self.db, "bind", None) is not None else ""
            if manifest_scope == "full":
                if sqlite_staging_file:
                    if "mode=memory" in db_url:
                        from .backup_service import BackupService
                        service = BackupService(self.db)
                        await service._restore_database(parts["database.json"])
                        await self.db.commit()
                        return
                    provider = SQLiteBackupProvider(self.db, str(self.db.bind.url))
                    await provider.restore_database(sqlite_staging_file)
                else:
                    # PG full restore
                    tmp_dir = Path(tempfile.mkdtemp(prefix="db-restore-prod-"))
                    db_restore_path = tmp_dir / "db.dump"
                    try:
                        db_restore_path.write_bytes(parts["db.dump"])
                        provider = provider_factory()
                        await provider.restore_database(db_restore_path)
                    finally:
                        shutil.rmtree(tmp_dir, ignore_errors=True)
            else:
                # Logical restore
                from .backup_service import BackupService
                service = BackupService(self.db) # For _restore_database which I should probably also move
                await service._restore_database(parts["database.json"])
                await self.db.commit()
        except Exception as e:
            raise RestorePromotionError(f"Database promotion failed: {e}")

    def promote_configs(self, configs_payload: Dict[str, Any], staging_config_dir: Path) -> None:
        try:
            from .backup_service import BackupService
            service = BackupService(self.db) # For _resolve_restore_path
            
            for entry in configs_payload.get("files", []):
                target = service._resolve_restore_path(entry["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                
                if target.exists():
                    bak_target = target.with_suffix(target.suffix + ".bak")
                    bak_target.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
                
                staging_src = staging_config_dir / target.relative_to(self.repo_root.resolve())
                target.write_text(staging_src.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception as e:
            raise RestorePromotionError(f"Config promotion failed: {e}")
