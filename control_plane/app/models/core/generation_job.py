import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    model_registry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=True, index=True)
    inference_backend_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("inference_backends.id"), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(64), default="/v1/chat/completions/async", nullable=False)
    requested_model: Mapped[str] = mapped_column(String(255), nullable=False)
    resolved_model: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False, index=True)
    is_stream: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    include_reasoning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    request_json: Mapped[str] = mapped_column(Text(), nullable=False)
    response_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    backend_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backend_errors_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    prompt_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_count_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tokens_estimated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0, nullable=False)
    max_tokens_requested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False) # QoS Priority
    
    # QoS Phase 24 fields
    qos_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    effective_priority: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True)
    dequeued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    queue_wait_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_limit_status: Mapped[str | None] = mapped_column(String(32), nullable=True) # allowed|throttled|rejected
    rate_limit_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    client = relationship("Client")
    model_registry = relationship("ModelRegistry")
    inference_backend = relationship("InferenceBackend", back_populates="generation_jobs")
