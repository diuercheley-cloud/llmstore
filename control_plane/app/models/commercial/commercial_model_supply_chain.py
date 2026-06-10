import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialSignedModelRegistryEntry(Base):
    __tablename__ = "commercial_signed_model_registry_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_alias: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    model_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    model_format: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    checksum_sha256: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_provenance_attestations.id"),
        nullable=True,
        index=True,
    )
    trust_state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    tenant_scope_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialModelProvenanceAttestation(Base):
    __tablename__ = "commercial_model_provenance_attestations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    imported_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_method: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    artifact_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    chain_of_custody_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialModelRevocationRecord(Base):
    __tablename__ = "commercial_model_revocation_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_signed_model_registry_entries.id"),
        nullable=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    revocation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    revoked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialModelPromotionBundle(Base):
    __tablename__ = "commercial_model_promotion_bundles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    target_cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialModelIntegrityScan(Base):
    __tablename__ = "commercial_model_integrity_scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_signed_model_registry_entries.id"),
        nullable=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scan_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    expected_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    integrity_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scan_duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialRuntimeModelAttestation(Base):
    __tablename__ = "commercial_runtime_model_attestations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_signed_model_registry_entries.id"),
        nullable=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    backend_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    model_alias: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    expected_manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    observed_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attestation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)


class CommercialModelIntegrityEvent(Base):
    __tablename__ = "commercial_model_integrity_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    registry_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_signed_model_registry_entries.id"),
        nullable=True,
        index=True,
    )
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    immutable_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
