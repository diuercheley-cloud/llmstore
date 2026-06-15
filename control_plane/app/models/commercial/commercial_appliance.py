import uuid
from datetime import UTC, datetime

from app.db.base import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID


class CommercialApplianceProfile(Base):
    __tablename__ = "commercial_appliance_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appliance_id = Column(String(128), nullable=False, unique=True)
    deployment_tier = Column(
        String(64), default="regulated"
    )  # airgap, government, defense, regulated

    is_offline_first = Column(Boolean, default=True)
    require_removable_media_auth = Column(Boolean, default=False)
    strict_chain_of_custody = Column(Boolean, default=True)

    last_sync_hash = Column(String(128), nullable=True)
    health_status = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class CommercialOfflineSyncManifest(Base):
    __tablename__ = "commercial_offline_sync_manifests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appliance_id = Column(
        String(128), ForeignKey("commercial_appliance_profiles.appliance_id"), nullable=False
    )

    manifest_hash = Column(String(128), nullable=False, index=True)
    sync_direction = Column(String(32), default="export")  # export|import
    payload_type = Column(String(64), nullable=False)  # models, policies, audits, receipts

    media_uuid = Column(String(128), nullable=True)  # ID of removable media
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class CommercialOfflineModelBundle(Base):
    __tablename__ = "commercial_offline_model_bundles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_hash = Column(String(128), nullable=False, index=True)
    model_name = Column(String(128), nullable=False)

    signed_registry_hash = Column(String(128), nullable=True)
    promotion_status = Column(String(32), default="staged")  # staged|promoted|rejected

    manifest_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_offline_sync_manifests.id"), nullable=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class CommercialOfflineAuditPackage(Base):
    __tablename__ = "commercial_offline_audit_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_hash = Column(String(128), nullable=False, index=True)
    time_window_start = Column(DateTime, nullable=False)
    time_window_end = Column(DateTime, nullable=False)

    includes_receipts = Column(Boolean, default=True)
    includes_governance_logs = Column(Boolean, default=True)
    export_status = Column(String(32), default="generated")  # generated|exported|verified

    manifest_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_offline_sync_manifests.id"), nullable=True
    )
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
