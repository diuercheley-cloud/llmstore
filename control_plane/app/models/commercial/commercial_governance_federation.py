import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialGovernanceFederationPeer(Base):
    __tablename__ = "commercial_governance_federation_peers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    peer_cluster_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    environment: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    sync_mode: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="trusted", nullable=False)
    last_policy_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_audit_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialFederatedPolicySync(Base):
    __tablename__ = "commercial_federated_policy_syncs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    bundle_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bundle_version: Mapped[str] = mapped_column(String(64), nullable=False)
    sync_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    conflict_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    target_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    records_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialFederatedAuditTrail(Base):
    __tablename__ = "commercial_federated_audit_trails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_cluster_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
