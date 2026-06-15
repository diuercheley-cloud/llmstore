import uuid
from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialPolicyRuntimeBundle(Base):
    __tablename__ = "commercial_policy_runtime_bundles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    rego_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_namespace: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )
    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CommercialPolicyEvaluation(Base):
    __tablename__ = "commercial_policy_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_runtime_bundles.id", ondelete="CASCADE"),
        index=True,
    )

    evaluation_mode: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # advisory, dry_run, enforce, sovereign_strict
    enforcement_result: Mapped[str] = mapped_column(String(32), nullable=False)  # allow, deny, warn
    decision_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    runtime_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class CommercialPolicySimulation(Base):
    __tablename__ = "commercial_policy_simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_runtime_bundles.id", ondelete="CASCADE"),
        index=True,
    )

    simulation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    expected_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actual_result: Mapped[str] = mapped_column(String(32), nullable=False)

    diff_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CommercialPolicyDecisionLog(Base):
    __tablename__ = "commercial_policy_decision_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_evaluations.id", ondelete="CASCADE"),
        index=True,
    )

    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(32), nullable=False)
    context_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CommercialPolicyViolation(Base):
    __tablename__ = "commercial_policy_violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_policy_evaluations.id", ondelete="CASCADE"),
        index=True,
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True
    )

    violation_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # low, medium, high, critical
    remediation_hints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
