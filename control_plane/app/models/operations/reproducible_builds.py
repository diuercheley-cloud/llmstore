from datetime import datetime
from uuid import UUID

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

REPRODUCIBLE_BUILD_SCOPES = (
    "plugin",
    "federation_bundle",
    "governance_artifact",
    "attestation",
    "compatibility_contract",
    "mixed",
)

REPRODUCIBILITY_STATUSES = (
    "proposed",
    "reproducible",
    "warning",
    "blocked",
    "revoked",
)

ARTIFACT_VERIFICATION_STATUSES = (
    "passed",
    "failed",
    "warning",
    "blocked",
)

REPRODUCIBILITY_VERIFICATION_TYPES = (
    "hash_replay",
    "lineage_verification",
    "environment_verification",
    "artifact_verification",
    "dependency_verification",
)

REPLAY_STATUSES = (
    "passed",
    "failed",
    "warning",
)


class ReproducibleBuildManifest(Base):
    __tablename__ = "reproducible_build_manifests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    build_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    build_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    deterministic_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    build_environment_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    build_manifest_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    reproducibility_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="proposed", index=True
    )
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ArtifactVerificationRecord(Base):
    __tablename__ = "artifact_verification_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    build_manifest_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reproducible_build_manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    artifact_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class SourceArtifactLineage(Base):
    __tablename__ = "source_artifact_lineage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    build_manifest_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reproducible_build_manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lineage_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    replay_verifiable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class BuildEnvironmentConstraint(Base):
    __tablename__ = "build_environment_constraints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    constraint_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    constraint_scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    required_determinism: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    offline_only: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    external_network_allowed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    external_dependency_resolution_allowed: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False
    )
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ReproducibilityVerificationResult(Base):
    __tablename__ = "reproducibility_verification_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    build_manifest_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reproducible_build_manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verification_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    reproducibility_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ArtifactReplayVerification(Base):
    __tablename__ = "artifact_replay_verifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_verification_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("artifact_verification_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    replay_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    replay_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    deterministic_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class ReproducibleBuildReceipt(Base):
    __tablename__ = "reproducible_build_receipts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    build_manifest_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("reproducible_build_manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
