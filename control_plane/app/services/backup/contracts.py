from __future__ import annotations
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pathlib import Path
from pydantic import BaseModel, Field
from app.schemas.backup import (
    BackupManifest, 
    BackupComponent, 
    BackupVerificationResult,
    BackupRestoreResult
)

# Standardized Result Objects
class BackupResult(BaseModel):
    manifest: BackupManifest
    payload_file: str
    encrypted_payload: bytes

class RestorePlan(BaseModel):
    backup_id: str
    steps: List[str]
    manifest: BackupManifest

# Protocols for Dependency Injection
@runtime_checkable
class CryptoProvider(Protocol):
    @property
    def key_id(self) -> str: ...
    def encrypt(self, data: bytes) -> bytes: ...
    def decrypt(self, data: bytes) -> bytes: ...
    def sign_payload(self, payload: Dict[str, Any]) -> str: ...
    def verify_signature(self, signature: str, payload: Dict[str, Any]) -> bool: ...

@runtime_checkable
class ArchiveProvider(Protocol):
    def create(self, payload_parts: Dict[str, bytes]) -> bytes: ...
    def extract(self, archive_bytes: bytes) -> Dict[str, Any]: ...

@runtime_checkable
class BackupManifestProvider(Protocol):
    def build_components(self, payload_parts: Dict[str, bytes]) -> List[BackupComponent]: ...
    def read(self, backup_root: Path, backup_id: str) -> BackupManifest: ...
    def write(self, backup_root: Path, manifest: BackupManifest) -> None: ...

@runtime_checkable
class RestorePlannerProvider(Protocol):
    def create_plan(self, manifest: BackupManifest) -> List[str]: ...

@runtime_checkable
class StagingProvider(Protocol):
    async def setup_staging_db(self, staging_dbname: str) -> tuple[str, Optional[str], Optional[Path]]: ...
    async def cleanup_staging(self, staging_dbname: Optional[str], sqlite_staging_file: Optional[Path]) -> None: ...
    async def validate_staging_db(self, staging_engine: Any, scope: str) -> Dict[str, Any]: ...

@runtime_checkable
class PromotionProvider(Protocol):
    async def promote_database(
        self, 
        manifest_scope: str, 
        parts: Dict[str, Any], 
        sqlite_staging_file: Optional[Path], 
        provider_factory: Any
    ) -> None: ...
    def promote_configs(self, configs_payload: Dict[str, Any], staging_config_dir: Path) -> None: ...

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
        key_id: Optional[str],
        source: str,
        target: str,
        result: str,
        checksum: Optional[str],
    ) -> None: ...
    async def record_admin_audit(
        self,
        event_type: str,
        status: str,
        actor: str,
        target_id: str,
        metadata: Dict[str, Any]
    ) -> None: ...
