from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BackupComponent(BaseModel):
    name: str
    description: str
    item_count: int
    data_hash: str
    file_name: str


class BackupManifest(BaseModel):
    backup_id: str = Field(default_factory=lambda: f"backup-{uuid4().hex[:12]}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "2.0.0"
    scope: str = "logical-agent-backup"
    coverage: str = "partial"
    included: list[str] = Field(
        default_factory=lambda: ["agents", "workflows", "embedding metadata"]
    )
    excluded: list[str] = Field(
        default_factory=lambda: [
            "auth",
            "tenants",
            "billing",
            "audit",
            "policies",
            "persisted config",
        ]
    )
    components: list[BackupComponent] = Field(default_factory=list)
    encryption_status: str = "encrypted"
    encryption_algorithm: str = "fernet"
    signature_status: str = "signed"
    signature_algorithm: str = "hmac-sha256"
    archive_checksum: str
    payload_file: str
    payload_signature: str
    pitr_supported: bool = False
    auto_verification_status: str = "pending"
    last_verified_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    key_id: str | None = None
    crypto_version: str | None = None
    algorithm: str | None = None
    crypto_created_at: str | None = None
    excluded_sensitive_files: list[str] = Field(default_factory=list)
    redacted_config_keys: list[str] = Field(default_factory=list)
    backup_type: str = "standard"


class BackupSummary(BaseModel):
    id: str
    created_at: datetime
    component_count: int
    status: str
    scope: str = "logical-agent-backup"
    archive_checksum: str
    backup_type: str = "standard"


class BackupVerificationEntry(BaseModel):
    name: str
    status: str
    expected_hash: str
    actual_hash: str | None = None


class BackupVerificationResult(BaseModel):
    backup_id: str
    status: str
    signature_valid: bool
    archive_checksum_valid: bool
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    component_verification: list[BackupVerificationEntry] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None


class BackupErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class BackupErrorResponse(BaseModel):
    error: BackupErrorDetail
    correlation_id: str | None = None


class BackupCreateRequest(BaseModel):
    full: bool | None = None
    scope: str = "logical-agent-backup"
    backup_type: str = "standard"


class BackupRestoreRequest(BaseModel):
    dry_run: bool = False


class BackupRestoreResult(BaseModel):
    backup_id: str
    status: str
    restored_components: list[str] = Field(default_factory=list)
    verification: BackupVerificationResult
    plan: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None


class RestoreRequestCreate(BaseModel):
    backup_id: str
    dry_run: bool = False


class RestoreRequestResponse(BaseModel):
    id: str
    backup_id: str
    status: str
    requester: str
    approver: str | None = None
    token: str | None = None
    dry_run: bool
    expires_at: datetime
    created_at: datetime
    approved_at: datetime | None = None
    executed_at: datetime | None = None


class RestoreRequestExecute(BaseModel):
    token: str
