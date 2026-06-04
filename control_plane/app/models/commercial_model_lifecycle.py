import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

VALID_LIFECYCLE_STATES = {
    "discovered",
    "staged",
    "pending_approval",
    "approved",
    "promoted",
    "quarantined",
    "revoked",
    "rolled_back",
    "archived",
}


class CommercialModelLifecycleRecord(Base):
    __tablename__ = "commercial_model_lifecycle_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_signed_model_registry_entries.id"),
        nullable=True,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_alias: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, default="discovered", index=True)
    previous_lifecycle_state: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    tenant_scope_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provenance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_provenance_attestations.id"),
        nullable=True,
        index=True,
    )
    attestation_bound: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checksum_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signature_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lineage_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sovereign_restricted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    export_restricted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    state_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialModelPromotionRequest(Base):
    __tablename__ = "commercial_model_promotion_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lifecycle_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_lifecycle_records.id"),
        nullable=False,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    approval_count_required: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approval_count_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_promotion_bundles.id"),
        nullable=True,
        index=True,
    )
    approval_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signed_manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    immutable_receipt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    media_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chain_of_custody_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialModelLineage(Base):
    __tablename__ = "commercial_model_lineages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lifecycle_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_lifecycle_records.id"),
        nullable=False,
        index=True,
    )
    parent_lineage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_lineages.id"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    derivation_method: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    artifact_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    predecessor_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provenance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_provenance_attestations.id"),
        nullable=True,
        index=True,
    )
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dag_node_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialModelRollbackRecord(Base):
    __tablename__ = "commercial_model_rollback_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lifecycle_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_lifecycle_records.id"),
        nullable=False,
        index=True,
    )
    promotion_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_promotion_requests.id"),
        nullable=True,
        index=True,
    )
    rollback_from_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rollback_to_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rollback_reason: Mapped[str] = mapped_column(Text, nullable=False)
    rolled_back_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    predecessor_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    checksum_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lineage_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attestation_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chain_of_custody_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    immutable_receipt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialOfflineModelVerification(Base):
    __tablename__ = "commercial_offline_model_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lifecycle_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_model_lifecycle_records.id"),
        nullable=True,
        index=True,
    )
    verification_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    checksum_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provenance_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    crl_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attestation_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lineage_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    overall_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    media_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    media_uuid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    signed_manifest: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
