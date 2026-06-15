from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from app.schemas.backup import (
    BackupComponent,
    BackupManifest,
)
from pydantic import BaseModel


# Standardized Result Objects
class BackupResult(BaseModel):
    manifest: BackupManifest
    payload_file: str
    encrypted_payload: bytes


class RestorePlan(BaseModel):
    backup_id: str
    steps: list[str]
    manifest: BackupManifest


# Protocols for Dependency Injection
@runtime_checkable
class CryptoProvider(Protocol):
    @property
    def key_id(self) -> str: ...
    def encrypt(self, data: bytes) -> bytes: ...
    def decrypt(self, data: bytes) -> bytes: ...
    def sign_payload(self, payload: dict[str, Any]) -> str: ...
    def verify_signature(self, signature: str, payload: dict[str, Any]) -> bool: ...


@runtime_checkable
class ArchiveProvider(Protocol):
    def create(self, payload_parts: dict[str, bytes]) -> bytes: ...
    def extract(self, archive_bytes: bytes) -> dict[str, Any]: ...


@runtime_checkable
class BackupManifestProvider(Protocol):
    def build_components(self, payload_parts: dict[str, bytes]) -> list[BackupComponent]: ...
    def read(self, backup_root: Path, backup_id: str) -> BackupManifest: ...
    def write(self, backup_root: Path, manifest: BackupManifest) -> None: ...


@runtime_checkable
class RestorePlannerProvider(Protocol):
    def create_plan(self, manifest: BackupManifest) -> list[str]: ...


@runtime_checkable
class StagingProvider(Protocol):
    async def setup_staging_db(
        self, staging_dbname: str
    ) -> tuple[str, str | None, Path | None]: ...
    async def cleanup_staging(
        self, staging_dbname: str | None, sqlite_staging_file: Path | None
    ) -> None: ...
    async def validate_staging_db(self, staging_engine: Any, scope: str) -> dict[str, Any]: ...


@runtime_checkable
class PromotionProvider(Protocol):
    async def promote_database(
        self,
        manifest_scope: str,
        parts: dict[str, Any],
        sqlite_staging_file: Path | None,
        provider_factory: Any,
    ) -> None: ...
    def promote_configs(
        self, configs_payload: dict[str, Any], staging_config_dir: Path
    ) -> None: ...


@runtime_checkable
class RollbackProvider(Protocol):
    async def perform_rollback(self, safety_backup_id: str) -> None: ...


@runtime_checkable
class AuditProvider(Protocol):
    async def log_immutable_event(
        self,
        *,
        action: str,
        actor: str,
        backup_id: str,
        key_id: str | None,
        source: str,
        target: str,
        result: str,
        checksum: str | None,
    ) -> None: ...
    async def record_admin_audit(
        self, event_type: str, status: str, actor: str, target_id: str, metadata: dict[str, Any]
    ) -> None: ...
