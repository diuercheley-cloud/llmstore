from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

CONTRACT_SCOPES = (
    "federation_bundle",
    "adapter_registry",
    "adapter_promotion",
    "attestation",
    "remediation",
    "governance",
    "mixed",
)

CONTRACT_STATUSES = (
    "active",
    "deprecated",
    "blocked",
    "superseded",
)

COMPATIBILITY_TYPES = (
    "backward",
    "forward",
    "bidirectional",
    "restricted",
)

COMPATIBILITY_STATUSES = (
    "compatible",
    "incompatible",
    "warning",
)

NEGOTIATION_STATUSES = (
    "proposed",
    "accepted",
    "rejected",
    "conflicted",
)

CAPABILITY_NEGOTIATION_STATUSES = (
    "proposed",
    "approved",
    "partially_approved",
    "denied",
)

DEPRECATION_STATUSES = (
    "proposed",
    "announced",
    "enforced",
    "completed",
)

VERIFICATION_STATUSES = (
    "passed",
    "failed",
    "warning",
)


class CompatibilityContract(Base):
    __tablename__ = "compatibility_contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    contract_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    semantic_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    compatibility_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    deterministic_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    contract_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class CompatibilityMatrix(Base):
    __tablename__ = "compatibility_matrices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    compatibility_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    compatibility_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    upgrade_supported: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    downgrade_supported: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VersionNegotiationSession(Base):
    __tablename__ = "version_negotiation_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    source_environment: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_environment: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    negotiated_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    negotiation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class CapabilityNegotiation(Base):
    __tablename__ = "capability_negotiations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    negotiation_session_id: Mapped[str] = mapped_column(String(64), ForeignKey("version_negotiation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    approved_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    denied_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    negotiation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FeatureCompatibilityFlag(Base):
    __tablename__ = "feature_compatibility_flags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    feature_scope: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    minimum_supported_version: Mapped[str] = mapped_column(String(32), nullable=False)
    maximum_supported_version: Mapped[str] = mapped_column(String(32), nullable=False)
    deprecated_after_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class DeprecationLifecycle(Base):
    __tablename__ = "deprecation_lifecycles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("compatibility_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    deprecation_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    deprecation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    replacement_contract: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    migration_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class CompatibilityVerificationResult(Base):
    __tablename__ = "compatibility_verification_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("compatibility_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    compatibility_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class CompatibilityReceipt(Base):
    __tablename__ = "compatibility_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("compatibility_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
