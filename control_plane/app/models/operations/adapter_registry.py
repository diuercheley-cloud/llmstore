import uuid
from datetime import datetime
from typing import Optional

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class SignedAdapterRegistryEntry(Base):
    __tablename__ = "signed_adapter_registry_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("adapter_manifests.id", ondelete="CASCADE"), nullable=False, index=True)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    registry_status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    registry_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    deterministic_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterRegistryPolicy(Base):
    __tablename__ = "adapter_registry_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    allowed_adapter_types_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    denied_capabilities_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    require_sandbox: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    require_dry_run_default: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    require_approval: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    allow_offline_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterRegistryDecision(Base):
    __tablename__ = "adapter_registry_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    registry_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("signed_adapter_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)  # submit, approve, reject, revoke, block, deprecate
    decision_status: Mapped[str] = mapped_column(String(50), nullable=False)  # accepted, denied
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    decided_by: Mapped[str] = mapped_column(String(100), nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterRegistryReceipt(Base):
    __tablename__ = "adapter_registry_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    registry_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("signed_adapter_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterRegistryBlocklistEntry(Base):
    __tablename__ = "adapter_registry_blocklist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterRegistryAllowlistEntry(Base):
    __tablename__ = "adapter_registry_allowlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
