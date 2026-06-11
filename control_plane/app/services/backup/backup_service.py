import io
import json
import os
import shutil
import hashlib
import time
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import get_settings
from app.db.base import Base
from app.schemas.backup import (
    BackupComponent,
    BackupCreateRequest,
    BackupManifest,
    BackupRestoreRequest,
    BackupRestoreResult,
    BackupSummary,
    BackupVerificationResult,
)
from app.core.request_context import get_correlation_id
from app.core.metrics import (
    BACKUP_DURATION_SECONDS,
    BACKUP_FAILURE_TOTAL,
    RESTORE_DURATION_SECONDS,
    RESTORE_FAILURE_TOTAL,
    MEASURED_RTO_SECONDS,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .archive import ArchiveService
from .audit import BackupAuditEmitter
from .crypto import BackupCryptoService
from .database_providers import PostgresBackupProvider, SQLiteBackupProvider
from .manifest import ManifestService
from .planner import RestorePlanner
from .redaction import ConfigRedactor
from .verification import BackupVerificationService
from .errors import BackupError, RestoreLockError, BackupValidationError, BackupManifestError

def _sha256_bytes(payload: bytes) -> str:
    import hashlib
    return hashlib.sha256(payload).hexdigest()

class BackupService:
    def __init__(
        self, 
        db: AsyncSession,
        crypto: Optional[BackupCryptoService] = None,
        audit: Optional[BackupAuditEmitter] = None,
        manifest_provider: Optional[ManifestService] = None,
        archive_provider: Optional[ArchiveService] = None,
        verification_provider: Optional[BackupVerificationService] = None,
        planner_provider: Optional[RestorePlanner] = None,
    ):
        self.db = db
        self.settings = get_settings()
        self.backup_root = Path(self.settings.disaster_recovery_backup_dir or "/tmp/agent-backups") / "system"
        self.repo_root = Path(
            getattr(self.settings, "llmstack_backup_source_root", None)
            or os.getenv("LLMSTACK_BACKUP_SOURCE_ROOT")
            or "/home/kleber/llm-inference-stack"
        )
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        self.crypto = crypto or BackupCryptoService()
        self._fernet = self.crypto._fernet
        self.audit = audit or BackupAuditEmitter(db)
        self.manifest_service = manifest_provider or ManifestService()
        self.archive_service = archive_provider or ArchiveService()
        self.verifier = verification_provider or BackupVerificationService(self.crypto)
        self.planner = planner_provider or RestorePlanner()

    def _log(self, level: int, msg: str, **kwargs):
        logging.getLogger(__name__).log(
            level,
            f"[BACKUP] {msg}",
            extra={
                "correlation_id": get_correlation_id(),
                "extra_data": kwargs,
            },
        )

    async def create_backup(self, request: BackupCreateRequest | None = None, actor: str = "system") -> BackupManifest:
        start_time = time.time()
        self._log(logging.INFO, f"Starting backup creation", actor=actor)
        try:
            req = request or BackupCreateRequest()
            scope = req.scope
            if req.full is True:
                scope = "full"
                
            if scope not in ("logical-agent-backup", "full"):
                raise BackupValidationError(f"Unsupported backup scope: {scope}")
                
            backup_id = f"backup-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{os.urandom(3).hex()}"
            redactor = ConfigRedactor()
            
            if scope == "full":
                tmp_dir = Path(tempfile.mkdtemp(prefix="db-dump-"))
                db_dump_path = tmp_dir / "db.dump"
                try:
                    provider = self._get_database_provider()
                    db_metadata = await provider.dump_database(db_dump_path)
                    db_dump_bytes = db_dump_path.read_bytes()
                    logical_payload = await self._build_payload_parts(redactor)
                    database_payload = json.loads(logical_payload["database.json"].decode("utf-8"))

                    def _subset_payload(table_names: list[str]) -> bytes:
                        tables = database_payload.get("tables", {})
                        subset_tables = {name: tables.get(name, []) for name in table_names if name in tables}
                        item_count = sum(len(rows) for rows in subset_tables.values())
                        return json.dumps(
                            {
                                "tables": subset_tables,
                                "item_count": item_count,
                            },
                            sort_keys=True,
                        ).encode("utf-8")

                    payload_parts = {
                        "db.dump": db_dump_bytes,
                        "database.json": logical_payload["database.json"],
                        "configs.json": logical_payload["configs.json"],
                        "feature_flags.json": logical_payload["feature_flags.json"],
                        "agents.json": _subset_payload(
                            [
                                "agent_definitions",
                                "agent_registry_entries",
                                "agent_versions",
                            ]
                        ),
                        "workflows.json": _subset_payload(
                            [
                                "agent_workflow_definitions",
                                "agent_workflow_nodes",
                                "agent_workflow_edges",
                            ]
                        ),
                        "embeddings_metadata.json": _subset_payload(
                            [
                                "agent_memory_items",
                                "agent_memory_indexes",
                            ]
                        ),
                    }
                finally:
                    shutil.rmtree(str(tmp_dir), ignore_errors=True)
            else:
                payload_parts = await self._build_payload_parts(redactor)
                db_metadata = {
                    "database_engine": self.settings.database_url.split(":", 1)[0],
                    "database_version": "unknown",
                    "schema_revision": "unknown",
                    "alembic_head": "unknown",
                    "dump_format": "logical-json",
                }

            components = self.manifest_service.build_components(payload_parts)
            archive_bytes = self.archive_service.create(payload_parts)
            encrypted_payload = self.crypto.encrypt(archive_bytes)
     
            manifest = BackupManifest(
                backup_id=backup_id,
                scope=scope,
                coverage="full" if scope == "full" else "partial",
                included=["database", "configs", "feature_flags"] if scope == "full" else ["agents", "workflows", "embedding metadata", "configs", "feature_flags"],
                excluded=[] if scope == "full" else ["auth", "tenants", "billing", "audit", "policies", "persisted config"],
                components=components,
                archive_checksum=hashlib.sha256(encrypted_payload).hexdigest(),
                payload_file="payload.tar.gz.enc",
                payload_signature=self.crypto.sign_payload(
                    {
                        "backup_id": backup_id,
                        "archive_checksum": hashlib.sha256(encrypted_payload).hexdigest(),
                        "components": [component.model_dump() for component in components],
                    }
                ),
                metadata={
                    "database_engine": db_metadata["database_engine"],
                    "database_version": db_metadata["database_version"],
                    "schema_revision": db_metadata["schema_revision"],
                    "alembic_head": db_metadata["alembic_head"],
                    "dump_format": db_metadata["dump_format"],
                },
                key_id=self.crypto.key_id,
            )

            self.manifest_service.write(self.backup_root, manifest)
            (self.backup_root / backup_id / manifest.payload_file).write_bytes(encrypted_payload)

            verification = await self.verify_backup(backup_id, actor=actor)
            manifest.auto_verification_status = verification.status
            manifest.last_verified_at = verification.verified_at
            self.manifest_service.write(self.backup_root, manifest)
            
            duration = time.time() - start_time
            BACKUP_DURATION_SECONDS.observe(duration)
            self._log(logging.INFO, f"Backup successful: {backup_id}", backup_id=backup_id, duration=duration)
            
            await self.audit.log_immutable_event(
                action="backup_created", actor=actor, backup_id=backup_id,
                key_id=manifest.key_id, source="active_system", target=manifest.payload_file,
                result="success", checksum=manifest.archive_checksum,
            )
            return manifest
        except Exception as e:
            BACKUP_FAILURE_TOTAL.inc()
            error_code = getattr(e, "error_code", "BACKUP_INTERNAL_ERROR")
            self._log(logging.ERROR, f"Backup failed: {e}", actor=actor, error_code=error_code)
            raise e

    async def list_backups(self) -> List[BackupSummary]:
        backups = []
        for backup_dir in self.backup_root.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith("backup-"):
                try:
                    manifest = self.manifest_service.read(self.backup_root, backup_dir.name)
                    backups.append(BackupSummary(
                        id=manifest.backup_id,
                        created_at=manifest.created_at,
                        component_count=len(manifest.components),
                        status="valid", # Simplification
                        scope=manifest.scope,
                        archive_checksum=manifest.archive_checksum,
                    ))
                except Exception:
                    continue
        return sorted(backups, key=lambda x: x.created_at, reverse=True)

    async def delete_backup(self, backup_id: str) -> None:
        backup_dir = self.backup_root / backup_id
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

    async def get_backup(self, backup_id: str, actor: str = "system") -> BackupManifest:
        return self.manifest_service.read(self.backup_root, backup_id)

    async def verify_backup(self, backup_id: str, actor: str = "system") -> BackupVerificationResult:
        try:
            manifest = self.manifest_service.read(self.backup_root, backup_id)
        except BackupManifestError as exc:
            from app.core.metrics import BACKUP_VERIFICATION_FAILURE_TOTAL

            BACKUP_VERIFICATION_FAILURE_TOTAL.labels(reason="manifest_invalid").inc()
            self._log(logging.WARNING, f"Backup manifest verification failed for {backup_id}", backup_id=backup_id, error_code=exc.error_code)
            raise
        payload_path = self.backup_root / backup_id / manifest.payload_file
        try:
            encrypted_payload = payload_path.read_bytes()
        except FileNotFoundError as exc:
            from app.core.metrics import BACKUP_VERIFICATION_FAILURE_TOTAL

            BACKUP_VERIFICATION_FAILURE_TOTAL.labels(reason="payload_missing").inc()
            raise BackupManifestError(
                f"Backup payload not found: {backup_id}",
                details={"backup_id": backup_id, "path": str(payload_path)},
            ) from exc
        
        result = await self.verifier.verify(manifest, encrypted_payload)

        await self.audit.log_immutable_event(
            action="backup_verified",
            actor=actor,
            backup_id=backup_id,
            key_id=manifest.key_id,
            source=manifest.payload_file,
            target="verification_check",
            result=result.status,
            checksum=manifest.archive_checksum,
        )
        return result

    async def restore_backup(self, backup_id: str, request: BackupRestoreRequest | None = None) -> BackupRestoreResult:
        # Legacy entry point, now mostly handled by RestoreStagingService for critical paths
        from .restore_staging_service import RestoreStagingService
        service = RestoreStagingService(self.db)
        return await service.restore_with_staging(backup_id, request)

    def _get_database_provider(self) -> Any:
        url = self.settings.database_url
        if url.startswith("postgresql") or url.startswith("postgres"):
            return PostgresBackupProvider(self.db, url)
        return SQLiteBackupProvider(self.db, url)

    async def log_immutable_event(self, **kwargs):
        await self.audit.log_immutable_event(**kwargs)

    async def _restore_backup_without_lock(self, backup_id: str) -> None:
        manifest = self._read_manifest(backup_id)
        parts = self._extract_payload_parts(backup_id, manifest)
        await self._apply_restore(manifest, parts)

    async def _apply_restore(self, manifest: BackupManifest, parts: Dict[str, Any]) -> None:
        if manifest.scope == "full":
            provider = self._get_database_provider()
            tmp_dir = Path(tempfile.mkdtemp(prefix="db-restore-direct-"))
            try:
                db_restore_path = tmp_dir / "db.dump"
                db_restore_path.write_bytes(parts["db.dump"])
                await provider.restore_database(db_restore_path)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            await self._restore_database(parts.get("database.json", {}))
        
        if "configs.json" in parts:
            for entry in parts["configs.json"].get("files", []):
                target = self._resolve_restore_path(entry["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(entry["content"], encoding="utf-8")
        
        if "feature_flags.json" in parts:
            self._restore_feature_flags(parts["feature_flags.json"])
        
        await self.db.commit()

    async def _restore_database(self, db_data: Dict[str, Any]) -> None:
        if not db_data or "tables" not in db_data:
            return
        models = self._database_models()
        for model in models:
            table_name = model.__tablename__
            if table_name in db_data["tables"]:
                for row_data in db_data["tables"][table_name]:
                    await self.db.merge(model(**self._deserialize_row(model, row_data)))
        await self.db.flush()

    def _read_manifest(self, backup_id: str) -> BackupManifest:
        return self.manifest_service.read(self.backup_root, backup_id)

    def _extract_payload_parts(self, backup_id: str, manifest: BackupManifest) -> Dict[str, Any]:
        payload_path = self.backup_root / backup_id / manifest.payload_file
        try:
            encrypted_payload = payload_path.read_bytes()
        except FileNotFoundError as exc:
            raise BackupManifestError(
                f"Backup payload not found: {backup_id}",
                details={"backup_id": backup_id, "path": str(payload_path)},
            ) from exc
        archive_bytes = self.crypto.decrypt(encrypted_payload)
        return self.archive_service.extract(archive_bytes)

    async def _build_payload_parts(self, redactor: ConfigRedactor) -> Dict[str, bytes]:
        # Logical backup builder
        parts = {}
        models = self._database_models()
        db_data = {"tables": {}, "item_count": 0}
        for model in models:
            stmt = select(model)
            res = await self.db.execute(stmt)
            rows = res.scalars().all()
            db_data["tables"][model.__tablename__] = [self._serialize_row(model, row) for row in rows]
            db_data["item_count"] += len(rows)
        
        parts["database.json"] = json.dumps(self._serialize_value(db_data), sort_keys=True).encode("utf-8")
        parts["configs.json"] = json.dumps(self._serialize_value(self._dump_configs(redactor)), sort_keys=True).encode("utf-8")
        parts["feature_flags.json"] = json.dumps(self._serialize_value(self._dump_feature_flags()), sort_keys=True).encode("utf-8")
        return parts

    def _database_models(self) -> List[Any]:
        # Keep the logical backup focused on the DR-relevant domain set.
        allowed_tables = {
            "agent_definitions",
            "agent_registry_entries",
            "agent_versions",
            "agent_memory_items",
            "agent_memory_indexes",
            "agent_workflow_definitions",
            "agent_workflow_nodes",
            "agent_workflow_edges",
            "billing_plans",
            "clients",
            "billing_invoices",
            "oauth_states",
            "user_sessions",
            "deterministic_policies",
            "policy_evaluation_results",
            "immutable_audit_logs",
            "admin_audit_events",
        }
        return [
            mapper.class_
            for mapper in Base.registry.mappers
            if getattr(mapper.class_, "__tablename__", "") in allowed_tables
        ]

    def _serialize_row(self, model: Any, row: Any) -> Dict[str, Any]:
        data = {}
        for column in model.__table__.columns:
            data[column.name] = getattr(row, column.name)
        return data

    def _deserialize_row(self, model: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import date as date_cls, datetime as datetime_cls
        from sqlalchemy import types as sa_types

        result: Dict[str, Any] = {}
        for column in model.__table__.columns:
            value = data.get(column.name)
            if value is None:
                result[column.name] = None
                continue
            if isinstance(value, str) and (
                "uuid" in column.type.__class__.__name__.lower()
                or isinstance(column.type, sa_types.Uuid)
            ):
                try:
                    result[column.name] = UUID(value)
                    continue
                except Exception:
                    pass
            if isinstance(value, str) and "datetime" in column.type.__class__.__name__.lower():
                try:
                    result[column.name] = datetime_cls.fromisoformat(value.replace("Z", "+00:00"))
                    continue
                except Exception:
                    pass
            if isinstance(value, str) and column.type.__class__.__name__.lower() == "date":
                try:
                    result[column.name] = date_cls.fromisoformat(value)
                    continue
                except Exception:
                    pass
            result[column.name] = value
        return result

    def _serialize_value(self, val: Any) -> Any:
        if isinstance(val, dict):
            return {k: self._serialize_value(v) for k, v in val.items()}
        if isinstance(val, list):
            return [self._serialize_value(v) for v in val]
        if isinstance(val, (datetime, date)):
            return val.isoformat()
        if isinstance(val, UUID):
            return str(val)
        if isinstance(val, Decimal):
            return str(val)
        return val

    def _dump_configs(self, redactor: ConfigRedactor) -> Dict[str, Any]:
        configs = {"files": []}
        config_dir = self.repo_root / "config"
        if config_dir.exists():
            for f in config_dir.glob("*.yaml"):
                content = f.read_text(encoding="utf-8")
                configs["files"].append({
                    "path": str(f.relative_to(self.repo_root)),
                    "content": redactor.redact_file_content(f, content)
                })
        version_file = self.repo_root / "VERSION"
        if version_file.exists():
            configs["files"].append({
                "path": str(version_file.relative_to(self.repo_root)),
                "content": version_file.read_text(encoding="utf-8"),
            })
        return configs

    def _dump_feature_flags(self) -> Dict[str, Any]:
        return {"flags": {}} # Placeholder

    def _resolve_restore_path(self, rel_path: str) -> Path:
        candidate = (self.repo_root / rel_path).resolve()
        repo_root = self.repo_root.resolve()
        if not candidate.is_relative_to(repo_root):
            raise ValueError("Directory traversal sequence detected in backup payload path.")
        return candidate

    def _restore_feature_flags(self, data: Dict[str, Any]) -> None:
        pass # Placeholder

    def _build_archive(self, payload_parts: Dict[str, Any]) -> bytes:
        normalized_parts: Dict[str, bytes] = {}
        for name, payload in payload_parts.items():
            if isinstance(payload, bytes):
                normalized_parts[name] = payload
            elif isinstance(payload, str):
                normalized_parts[name] = payload.encode("utf-8")
            else:
                normalized_parts[name] = json.dumps(payload, sort_keys=True).encode("utf-8")
        return self.archive_service.create(normalized_parts)

    def _sign_payload(self, payload: dict[str, Any]) -> str:
        return self.crypto.sign_payload(payload)
import tempfile
