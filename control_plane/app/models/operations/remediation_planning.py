import uuid
import hashlib
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, Float, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base

def compute_deterministic_hash(*, fields: dict, version: str = "v1") -> str:
    """Computes a deterministic SHA-256 hash for a dictionary of fields."""
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{version}:{raw}".encode("utf-8")).hexdigest()

class RemediationPlan(Base):
    __tablename__ = "remediation_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., forecast, risk_assessment, correlation
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., low, medium, high, critical
    blast_radius: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., low, medium, high, critical
    requires_approval: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    deterministic_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="proposed", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationStep(Base):
    __tablename__ = "remediation_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    expected_effect: Mapped[str] = mapped_column(String(1000), nullable=False)
    reversible: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationPlanReceipt(Base):
    __tablename__ = "remediation_plan_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature_placeholder: Mapped[str] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RemediationApprovalRequirement(Base):
    __tablename__ = "remediation_approval_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("remediation_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    approval_scope: Mapped[str] = mapped_column(String(100), nullable=False)
    required_role: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
