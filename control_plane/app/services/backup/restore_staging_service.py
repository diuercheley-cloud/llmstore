import os
import shutil
import tempfile
import uuid
import logging
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import get_settings
from app.db.base import Base
from app.schemas.backup import BackupManifest, BackupRestoreResult, BackupRestoreRequest, BackupCreateRequest
from app.core.request_context import get_correlation_id
from app.core.metrics import (
    RESTORE_DURATION_SECONDS, 
    RESTORE_FAILURE_TOTAL, 
    MEASURED_RTO_SECONDS,
    RESTORE_STAGING_DURATION_SECONDS,
    RESTORE_PROMOTION_DURATION_SECONDS,
    RESTORE_ROLLBACK_DURATION_SECONDS
)
from .backup_service import BackupService
from .database_providers import SQLiteBackupProvider, PostgresBackupProvider
from .restore_lock_service import RestoreLockService
from .staging import RestoreStagingService as StagingLogic
from .promotion import RestorePromotionService
from .rollback import RestoreRollbackService
from .planner import RestorePlanner
from .contracts import StagingProvider, PromotionProvider, RollbackProvider
from .errors import RestoreStagingError, RestorePromotionError, RestoreRollbackError, RestoreLockError

logger = logging.getLogger(__name__)

class RestoreStagingService:
    def __init__(
        self, 
        db: AsyncSession,
        staging_provider: Optional[StagingProvider] = None,
        promotion_provider: Optional[PromotionProvider] = None,
        rollback_provider: Optional[RollbackProvider] = None,
        backup_service: Optional[BackupService] = None
    ):
        self.db = db
        self.settings = get_settings()
        self.backup_service = backup_service or BackupService(db)
        self.staging_logic = staging_provider or StagingLogic(db, self.settings.database_url)
        self.promotion_service = promotion_provider or RestorePromotionService(db, self.backup_service.repo_root)
        self.rollback_service = rollback_provider or RestoreRollbackService(db)
        self.restore_state_path = self.backup_service.backup_root / "restore-state.json"

    def _log(self, level: int, msg: str, **kwargs):
        logger.log(
            level,
            f"[RESTORE] {msg}",
            extra={
                "correlation_id": get_correlation_id(),
                "extra_data": kwargs,
            },
        )

    def _load_restore_state(self) -> dict[str, Any]:
        if not self.restore_state_path.exists():
            return {}
        try:
            return json.loads(self.restore_state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_restore_state(self, payload: dict[str, Any]) -> None:
        self.restore_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.restore_state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _idempotent_restore_result(
        self,
        backup_id: str,
        manifest,
        verification,
        plan,
        *,
        safety_id: str | None,
    ) -> BackupRestoreResult:
        return BackupRestoreResult(
            backup_id=backup_id,
            status="restored",
            restored_components=[c.name for c in manifest.components],
            verification=verification,
            plan=plan,
            details={
                "validation_report": {"valid": True, "errors": [], "idempotent": True},
                "pre_restore_backup_id": safety_id,
                "idempotent": True,
            },
        )

    async def restore_with_staging(self, backup_id: str, request: BackupRestoreRequest | None = None, actor: str = "system") -> BackupRestoreResult:
        start_time = time.time()
        self._log(logging.INFO, f"Starting restore for backup {backup_id}", backup_id=backup_id, actor=actor)
        try:
            result = await self._restore_with_staging_impl(backup_id, request, actor)
            duration = time.time() - start_time
            RESTORE_DURATION_SECONDS.observe(duration)
            if result.status == "restored":
                MEASURED_RTO_SECONDS.set(duration)
                self._log(logging.INFO, f"Restore successful for backup {backup_id}", backup_id=backup_id, duration=duration)
            elif result.status in ("failed", "blocked"):
                RESTORE_FAILURE_TOTAL.inc()
                self._log(logging.WARNING, f"Restore {result.status} for backup {backup_id}", backup_id=backup_id, error_code=result.error_code)
            return result
        except Exception as e:
            RESTORE_FAILURE_TOTAL.inc()
            error_code = getattr(e, "error_code", "RESTORE_INTERNAL_ERROR")
            self._log(logging.ERROR, f"Restore failed for backup {backup_id}: {e}", backup_id=backup_id, error_code=error_code)
            raise e

    async def _restore_with_staging_impl(self, backup_id: str, request: BackupRestoreRequest | None = None, actor: str = "system") -> BackupRestoreResult:
        req = request or BackupRestoreRequest()
        verification = await self.backup_service.verify_backup(backup_id, actor=actor)
        manifest = self.backup_service._read_manifest(backup_id)
        plan = self.backup_service.planner.create_plan(manifest)
        
        validation_report = {
            "manifest_valid": True,
            "signature_valid": verification.signature_valid,
            "checksums_valid": verification.archive_checksum_valid,
            "database_valid": False,
            "alembic_head": "none",
            "verified_tables": [],
            "missing_tables": [],
            "components_valid": True,
            "errors": []
        }

        # Log restore_requested
        await self.backup_service.log_immutable_event(
            action="restore_requested", actor=actor, backup_id=backup_id,
            key_id=manifest.key_id, source=manifest.payload_file,
            target="active_system", result="pending", checksum=manifest.archive_checksum,
        )
        await self.db.commit()

        if verification.status != "valid":
            validation_report["manifest_valid"] = False
            validation_report["errors"].append("Backup verification failed")
            await self.backup_service.log_immutable_event(action="restore_failed", actor=actor, backup_id=backup_id, result="failed: verification failed", key_id=manifest.key_id, source=manifest.payload_file, target="active_system", checksum=manifest.archive_checksum)
            return BackupRestoreResult(
                backup_id=backup_id, 
                status="blocked", 
                verification=verification, 
                plan=plan, 
                details={"reason": "verification failed", "validation_report": validation_report},
                error_code=verification.error_code
            )

        parts = self.backup_service._extract_payload_parts(backup_id, manifest)

        restore_state = self._load_restore_state()
        if (
            not req.dry_run
            and restore_state.get("backup_id") == backup_id
            and restore_state.get("archive_checksum") == manifest.archive_checksum
            and restore_state.get("status") == "restored"
        ):
            self._log(
                logging.INFO,
                f"Restore replay skipped for backup {backup_id}",
                backup_id=backup_id,
                actor=actor,
                idempotent=True,
            )
            return self._idempotent_restore_result(
                backup_id,
                manifest,
                verification,
                plan,
                safety_id=restore_state.get("pre_restore_backup_id"),
            )
        
        # Staging
        staging_dbname = f"dbname_staging_{uuid.uuid4().hex[:8]}"
        staging_config_dir = Path(tempfile.mkdtemp(prefix="staging-configs-"))
        
        staging_start = time.time()
        try:
            staging_db_url, pg_dbname, sqlite_file = await self.staging_logic.setup_staging_db(staging_dbname)
        except Exception as exc:
            RESTORE_STAGING_DURATION_SECONDS.observe(time.time() - staging_start)
            await self.backup_service.log_immutable_event(
                action="restore_failed",
                actor=actor,
                backup_id=backup_id,
                result=f"failed: staging setup failed: {exc}",
                key_id=manifest.key_id,
                source=manifest.payload_file,
                target="active_system",
                checksum=manifest.archive_checksum,
            )
            return await self._fail_restore(
                backup_id,
                manifest,
                verification,
                plan,
                validation_report,
                f"Staging setup failed: {exc}",
                actor,
                error_code=RestoreStagingError.error_code,
            )

        lock_service = RestoreLockService(self.db)
        if not req.dry_run and not await lock_service.acquire_lock():
            await self.staging_logic.cleanup_staging(pg_dbname, sqlite_file)
            shutil.rmtree(staging_config_dir, ignore_errors=True)
            raise RestoreLockError(
                "Lock acquisition failed: A restore is already in progress.",
                details={"backup_id": backup_id},
            )

        try:
            # Load into staging
            staging_engine = create_async_engine(staging_db_url)
            staging_session_maker = async_sessionmaker(staging_engine, expire_on_commit=False, class_=AsyncSession)
            
            if manifest.scope == "full":
                if pg_dbname:
                    provider = PostgresBackupProvider(None, staging_db_url)
                    tmp_dir = Path(tempfile.mkdtemp(prefix="db-restore-staging-"))
                    try:
                        db_restore_path = tmp_dir / "db.dump"
                        db_restore_path.write_bytes(parts["db.dump"])
                        await provider.restore_database(db_restore_path)
                    finally:
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                else:
                    async with staging_session_maker() as staging_session:
                        provider = SQLiteBackupProvider(staging_session, staging_db_url)
                        tmp_dir = Path(tempfile.mkdtemp(prefix="db-restore-staging-"))
                        try:
                            db_restore_path = tmp_dir / "db.dump"
                            db_restore_path.write_bytes(parts["db.dump"])
                            await provider.restore_database(db_restore_path)
                        finally:
                            shutil.rmtree(tmp_dir, ignore_errors=True)
            else:
                async with staging_engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                async with staging_session_maker() as staging_session:
                    db_part = parts.get("database.json")
                    if isinstance(db_part, dict):
                        models = self.backup_service._database_models()
                        for model in models:
                            for row in db_part.get("tables", {}).get(model.__tablename__, []):
                                await staging_session.merge(model(**self.backup_service._deserialize_row(model, row)))
                        await staging_session.commit()

            # Configs to staging
            for entry in parts.get("configs.json", {}).get("files", []):
                target = self.backup_service._resolve_restore_path(entry["path"])
                staging_target = staging_config_dir / target.relative_to(self.backup_service.repo_root.resolve())
                staging_target.parent.mkdir(parents=True, exist_ok=True)
                staging_target.write_text(entry["content"], encoding="utf-8")

            # Validate staging
            report = await self.staging_logic.validate_staging_db(staging_engine, manifest.scope)
            validation_report.update(report)
            await staging_engine.dispose()
            
            RESTORE_STAGING_DURATION_SECONDS.observe(time.time() - staging_start)

            if not validation_report.get("valid", False):
                return await self._fail_restore(backup_id, manifest, verification, plan, validation_report, "Staging validation failed", actor, error_code=RestoreStagingError.error_code)

            if req.dry_run:
                return BackupRestoreResult(
                    backup_id=backup_id,
                    status="dry_run_complete",
                    verification=verification,
                    plan=plan,
                    details={"validation_report": validation_report, "side_effects_prevented": True},
                )

            # Promotion
            promotion_start = time.time()
            await self.backup_service.log_immutable_event(action="restore_approved", actor=actor, backup_id=backup_id, result="approved", key_id=manifest.key_id, source=manifest.payload_file, target="active_system", checksum=manifest.archive_checksum)
            await self.db.commit()

            safety_backup = await self.backup_service.create_backup(BackupCreateRequest(scope=manifest.scope, backup_type="pre-restore-safety-backup"), actor=actor)
            safety_id = safety_backup.backup_id

            await self.backup_service.log_immutable_event(
                action="restore_started", actor=actor, backup_id=backup_id, result="started",
                key_id=manifest.key_id, source=manifest.payload_file, target="active_system",
                checksum=manifest.archive_checksum
            )
            await self.db.commit()

            try:
                await self.promotion_service.promote_database(manifest.scope, parts, sqlite_file, self.backup_service._get_database_provider)
                if "configs.json" in parts:
                    self.promotion_service.promote_configs(parts["configs.json"], staging_config_dir)
                if "feature_flags.json" in parts:
                    self.backup_service._restore_feature_flags(parts["feature_flags.json"])
                await self.db.commit()
                RESTORE_PROMOTION_DURATION_SECONDS.observe(time.time() - promotion_start)
            except Exception as e:
                RESTORE_PROMOTION_DURATION_SECONDS.observe(time.time() - promotion_start)
                logger.error(f"Promotion failed: {e}. Rolling back...")
                
                rollback_start = time.time()
                try:
                    await self.backup_service.log_immutable_event(
                        action="rollback_started", actor=actor, backup_id=backup_id,
                        result="started", key_id=manifest.key_id, source=manifest.payload_file,
                        target="active_system", checksum=manifest.archive_checksum
                    )
                    await self.db.commit()

                    await self.rollback_service.perform_rollback(safety_id)
                    RESTORE_ROLLBACK_DURATION_SECONDS.observe(time.time() - rollback_start)

                    await self.backup_service.log_immutable_event(
                        action="rollback_completed", actor=actor, backup_id=backup_id,
                        result="success", key_id=manifest.key_id, source=manifest.payload_file,
                        target="active_system", checksum=manifest.archive_checksum
                    )
                    await self.db.commit()

                    return await self._fail_restore(backup_id, manifest, verification, plan, validation_report, f"Promotion failed: {e}", actor, safety_id, "success", error_code=RestorePromotionError.error_code)
                except Exception as rb_err:
                    RESTORE_ROLLBACK_DURATION_SECONDS.observe(time.time() - rollback_start)
                    logger.critical(f"CRITICAL: Rollback failed after failed promotion: {rb_err}")

                    await self.backup_service.log_immutable_event(
                        action="rollback_completed", actor=actor, backup_id=backup_id,
                        result=f"failed: {rb_err}", key_id=manifest.key_id, source=manifest.payload_file,
                        target="active_system", checksum=manifest.archive_checksum
                    )
                    await self.db.commit()

                    return await self._fail_restore(backup_id, manifest, verification, plan, validation_report, f"Promotion failed: {e}. Rollback ALSO FAILED: {rb_err}", actor, safety_id, "failed", error_code=RestoreRollbackError.error_code)

            await self.backup_service.log_immutable_event(action="restore_completed", actor=actor, backup_id=backup_id, result="success", key_id=manifest.key_id, source=manifest.payload_file, target="active_system", checksum=manifest.archive_checksum)
            await self.db.commit()
            self._write_restore_state(
                {
                    "backup_id": backup_id,
                    "archive_checksum": manifest.archive_checksum,
                    "status": "restored",
                    "pre_restore_backup_id": safety_id,
                    "actor": actor,
                    "correlation_id": get_correlation_id(),
                    "completed_at": time.time(),
                }
            )
            return BackupRestoreResult(
                backup_id=backup_id,
                status="restored",
                restored_components=[c.name for c in manifest.components],
                verification=verification,
                plan=plan,
                details={"validation_report": validation_report, "pre_restore_backup_id": safety_id},
            )

        finally:
            await self.staging_logic.cleanup_staging(pg_dbname, sqlite_file)
            shutil.rmtree(staging_config_dir, ignore_errors=True)
            if not req.dry_run:
                await lock_service.release_lock()

    async def _fail_restore(self, backup_id, manifest, verification, plan, report, reason, actor, safety_id=None, rollback_status="none", error_code=None):
        await self.backup_service.log_immutable_event(action="restore_failed", actor=actor, backup_id=backup_id, result=f"failed: {reason}", key_id=manifest.key_id, source=manifest.payload_file, target="active_system", checksum=manifest.archive_checksum)
        await self.db.commit()
        return BackupRestoreResult(backup_id=backup_id, status="failed", verification=verification, plan=plan, details={"reason": reason, "validation_report": report, "pre_restore_backup_id": safety_id, "rollback_status": rollback_status}, error_code=error_code)
