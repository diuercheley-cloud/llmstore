from __future__ import annotations

import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialAutonomousExecutionPolicy(Base):
    __tablename__ = "commercial_autonomous_execution_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    policy_bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_bundles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="guarded_enforce", index=True
    )
    max_blast_radius_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.35)
    require_human_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_stages_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    guarded_window_start: Mapped[str | None] = mapped_column(String(8), nullable=True)
    guarded_window_end: Mapped[str | None] = mapped_column(String(8), nullable=True)
    runtime_freeze_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    sovereign_hard_stop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rollback_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_signed_model_promotion: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class CommercialExecutionBlastRadius(Base):
    __tablename__ = "commercial_execution_blast_radius"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    risk_vector_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    blast_radius_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, index=True
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="low", index=True)
    reproducibility_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class CommercialExecutionGuardrailEvent(Base):
    __tablename__ = "commercial_execution_guardrail_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium", index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, default="blocked", index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class CommercialHumanApprovalCheckpoint(Base):
    __tablename__ = "commercial_human_approval_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_autonomous_execution_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_chain_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_approval_chains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    checkpoint_stage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approvals_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rejections_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class CommercialAutonomousExecutionReceipt(Base):
    __tablename__ = "commercial_autonomous_execution_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_autonomous_execution_policies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_human_approval_checkpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    blast_radius_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_execution_blast_radius.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    guardrail_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_execution_guardrail_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    execution_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="guarded", index=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    approval_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receipt_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    previous_receipt_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    detached_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    receipt_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
