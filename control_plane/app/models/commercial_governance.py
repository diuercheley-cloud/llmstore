import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommercialPolicyBundle(Base):
    __tablename__ = "commercial_policy_bundles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    bundle_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bundle_version: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # routing|billing|qos|revenue_protection|compliance|operational|global
    
    mode: Mapped[str] = mapped_column(String(32), default="dry_run", nullable=False)
    # disabled|dry_run|enforce
    
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    # draft|published|active|deprecated|rolled_back
    
    rules_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    artifacts = relationship("CommercialPolicyArtifact", back_populates="bundle", cascade="all, delete-orphan")
    approvals = relationship("CommercialPolicyApproval", back_populates="bundle", cascade="all, delete-orphan")
    drift_events = relationship("CommercialPolicyDriftEvent", back_populates="bundle")


class CommercialPolicyArtifact(Base):
    __tablename__ = "commercial_policy_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # json|snapshot|export|signature|simulation
    
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    bundle = relationship("CommercialPolicyBundle", back_populates="artifacts")


class CommercialPolicyApproval(Base):
    __tablename__ = "commercial_policy_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approval_chain_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_approval_chains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    # pending|approved|rejected|expired
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bundle = relationship("CommercialPolicyBundle", back_populates="approvals")
    approval_chain = relationship("CommercialApprovalChain")


class CommercialPolicyDriftEvent(Base):
    __tablename__ = "commercial_policy_drift_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_bundles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    drift_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # config_drift|runtime_override|manual_change|missing_rule|stale_bundle
    
    severity: Mapped[str] = mapped_column(String(32), default="low", nullable=False, index=True)
    # low|medium|high|critical
    
    expected_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drift_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bundle = relationship("CommercialPolicyBundle", back_populates="drift_events")
