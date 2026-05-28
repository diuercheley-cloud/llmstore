from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base

ENVIRONMENT_TYPES = (
    "sovereign_cluster",
    "sovereign_appliance",
    "airgap_node",
    "offline_staging",
    "federation_gateway",
)

TRUST_LEVELS = (
    "restricted",
    "trusted",
    "verified",
    "isolated",
)

SYNC_STATUSES = (
    "proposed",
    "exported",
    "imported",
    "verified",
    "conflicted",
    "rejected",
    "rolled_back",
)

BUNDLE_TYPES = (
    "attestation",
    "registry",
    "promotion",
    "remediation",
    "governance",
    "mixed",
)

BUNDLE_STATUSES = (
    "created",
    "exported",
    "imported",
    "verified",
    "conflicted",
    "rejected",
)

NEGOTIATION_STATUSES = (
    "proposed",
    "accepted",
    "denied",
    "expired",
)

CONFLICT_TYPES = (
    "lineage_conflict",
    "bundle_hash_conflict",
    "trust_policy_conflict",
    "replay_conflict",
    "version_conflict",
)

RESOLUTION_STRATEGIES = (
    "reject",
    "deterministic_merge",
    "keep_source",
    "keep_target",
    "manual_review_required",
)

RESOLUTION_STATUSES = (
    "proposed",
    "resolved",
    "blocked",
)


class SovereignFederationEnvironment(Base):
    __tablename__ = "sovereign_federation_environments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    environment_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    federation_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), nullable=False, default="restricted", index=True)
    offline_only: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    deterministic_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    environment_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FederationSynchronizationSession(Base):
    __tablename__ = "federation_synchronization_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    source_environment_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_federation_environments.id", ondelete="CASCADE"), nullable=False, index=True)
    target_environment_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_federation_environments.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_scope: Mapped[str] = mapped_column(String(255), nullable=False)
    sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    lineage_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    deterministic_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    session_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FederationSynchronizationBundle(Base):
    __tablename__ = "federation_synchronization_bundles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("federation_synchronization_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    bundle_name: Mapped[str] = mapped_column(String(120), nullable=False)
    bundle_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    bundle_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    lineage_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_bundle_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    replay_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bundle_status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FederationTrustNegotiation(Base):
    __tablename__ = "federation_trust_negotiations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    source_environment_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_federation_environments.id", ondelete="CASCADE"), nullable=False, index=True)
    target_environment_id: Mapped[str] = mapped_column(String(64), ForeignKey("sovereign_federation_environments.id", ondelete="CASCADE"), nullable=False, index=True)
    negotiation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    required_trust_level: Mapped[str] = mapped_column(String(32), nullable=False)
    negotiated_trust_level: Mapped[str] = mapped_column(String(32), nullable=False)
    replay_verification_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_verification_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FederationConflictResolution(Base):
    __tablename__ = "federation_conflict_resolutions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("federation_synchronization_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    conflict_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resolution_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed", index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FederationSynchronizationReceipt(Base):
    __tablename__ = "federation_synchronization_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("federation_synchronization_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature_placeholder: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class FederationLineageLink(Base):
    __tablename__ = "federation_lineage_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    bundle_id: Mapped[str] = mapped_column(String(64), ForeignKey("federation_synchronization_bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_bundle_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    lineage_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
