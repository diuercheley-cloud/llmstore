import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def compute_deterministic_hash(*, fields: dict, version: str = "v1") -> str:
    """Computes a deterministic SHA-256 hash for a dictionary of fields."""
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{version}:{raw}".encode("utf-8")).hexdigest()

class RemediationExecution(Base):
    __tablename__ = "remediation_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(50), nullable=False)  # simulation, approved_execution
    dry_run: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    approval_verified: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    kill_switch_checked: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    blast_radius_checked: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    rollback_plan_present: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True) # pending, approved, running, succeeded, failed, cancelled, rolled_back
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deterministic_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True, unique=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationExecutionStep(Base):
    __tablename__ = "remediation_execution_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_steps.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    output_summary: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    simulated_result_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationRollbackPlan(Base):
    __tablename__ = "remediation_rollback_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_executions.id", ondelete="CASCADE"), nullable=True, index=True)
    rollback_strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    rollback_steps_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationExecutionReceipt(Base):
    __tablename__ = "remediation_execution_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(100), nullable=False) # pre_execution, post_execution
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationKillSwitchState(Base):
    __tablename__ = "remediation_kill_switch_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
