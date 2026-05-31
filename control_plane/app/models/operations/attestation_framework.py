from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base

ATTESTATION_TYPES = (
    "workflow",
    "remediation",
    "execution",
    "adapter_registry",
    "adapter_promotion",
    "sandbox_run",
    "federation_bundle",
)

ATTESTATION_STATUSES = (
    "proposed",
    "issued",
    "verified",
    "revoked",
    "expired",
)

BUNDLE_STATUSES = (
    "draft",
    "exported",
    "imported",
    "verified",
    "rejected",
)

VERIFICATION_STATUSES = (
    "passed",
    "failed",
    "warning",
)


class SovereignExecutionAttestation(Base):
    __tablename__ = "sovereign_execution_attestations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    attestation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    attestation_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    attestation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="issued", index=True)
    deterministic_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attestation_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_attestation_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    attestation_chain_position: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AttestationTrustPolicy(Base):
    __tablename__ = "attestation_trust_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(120), nullable=False)
    allowed_attestation_types_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    require_chain_integrity: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    require_replay_verification: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    require_offline_verification: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    require_signature: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    federation_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AttestationFederationBundle(Base):
    __tablename__ = "attestation_federation_bundles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    bundle_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bundle_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    bundle_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    source_environment: Mapped[str] = mapped_column(String(120), nullable=False)
    target_environment: Mapped[str] = mapped_column(String(120), nullable=False)
    bundle_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AttestationVerificationResult(Base):
    __tablename__ = "attestation_verification_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    attestation_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_execution_attestations.id", ondelete="CASCADE"), nullable=False, index=True)
    verification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    verification_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    replay_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    chain_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    offline_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AttestationReceipt(Base):
    __tablename__ = "attestation_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    attestation_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_execution_attestations.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class AttestationChainLink(Base):
    __tablename__ = "attestation_chain_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    attestation_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_execution_attestations.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_link_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_link_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    chain_position: Mapped[str] = mapped_column(String(32), nullable=False)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
