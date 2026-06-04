import uuid
from datetime import datetime
from typing import Optional

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class AdapterPromotionWorkflow(Base):
    __tablename__ = "adapter_promotion_workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    registry_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("signed_adapter_registry_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    adapter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(50), default="draft", nullable=False) # draft, sandboxed, registry_approved, staging_simulated, production_eligible
    target_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    promotion_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False) # pending, blocked, approved, simulated, promoted, rolled_back, failed
    deterministic_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AdapterPromotionGateResult(Base):
    __tablename__ = "adapter_promotion_gate_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("adapter_promotion_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    gate_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gate_status: Mapped[str] = mapped_column(String(50), nullable=False) # passed, failed, skipped
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterPromotionStageTransition(Base):
    __tablename__ = "adapter_promotion_stage_transitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("adapter_promotion_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    transition_status: Mapped[str] = mapped_column(String(50), nullable=False) # proposed, allowed, blocked, completed, rolled_back
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterPromotionReceipt(Base):
    __tablename__ = "adapter_promotion_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("adapter_promotion_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    receipt_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AdapterPromotionRollback(Base):
    __tablename__ = "adapter_promotion_rollbacks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("adapter_promotion_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    rollback_to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    rollback_status: Mapped[str] = mapped_column(String(50), nullable=False) # proposed, completed, blocked
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
