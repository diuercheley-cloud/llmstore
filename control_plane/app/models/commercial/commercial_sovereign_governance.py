import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialAirgapSyncPackage(Base):
    __tablename__ = "commercial_airgap_sync_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    package_version: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False, index=True)
    file_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chain_of_custody_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialOfflineRevocationList(Base):
    __tablename__ = "commercial_offline_revocation_lists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crl_version: Mapped[str] = mapped_column(String(64), nullable=False)
    revoked_key_fingerprints_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    revoked_bundle_hashes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    revoked_peer_ids_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialHardwareAttestationRecord(Base):
    __tablename__ = "commercial_hardware_attestation_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    attestation_type: Mapped[str] = mapped_column(
        String(32), default="placeholder", nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False, index=True)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
