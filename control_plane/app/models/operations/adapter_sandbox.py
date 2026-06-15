import hashlib
import json
import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def compute_deterministic_hash(*, fields: dict, version: str = "v1") -> str:
    """Computes a deterministic SHA-256 hash for a dictionary of fields."""
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{version}:{raw}".encode()).hexdigest()


class AdapterManifest(Base):
    __tablename__ = "adapter_manifests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    denied_capabilities_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    sandbox_required: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    dry_run_default: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    network_access_allowed: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    subprocess_allowed: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    external_system_access_allowed: Mapped[bool] = mapped_column(
        Boolean(), default=False, nullable=False
    )
    deterministic_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AdapterSandboxRun(Base):
    __tablename__ = "adapter_sandbox_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    manifest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapter_manifests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("remediation_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("remediation_plans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    sandbox_mode: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # simulation, contract_validation
    dry_run: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    approval_verified: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    gates_verified: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AdapterSandboxStepResult(Base):
    __tablename__ = "adapter_sandbox_step_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sandbox_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapter_sandbox_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_domain: Mapped[str] = mapped_column(String(100), nullable=False)
    result_status: Mapped[str] = mapped_column(String(50), nullable=False)
    simulated_output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AdapterSandboxPolicyViolation(Base):
    __tablename__ = "adapter_sandbox_policy_violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapter_manifests.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    sandbox_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapter_sandbox_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    violation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # low, medium, high, critical
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AdapterSandboxReceipt(Base):
    __tablename__ = "adapter_sandbox_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sandbox_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adapter_sandbox_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    receipt_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # manifest_registration, sandbox_run, policy_violation
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
