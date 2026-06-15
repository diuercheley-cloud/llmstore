import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class InferenceRoutingDecision(Base):
    __tablename__ = "inference_routing_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_backend: Mapped[str | None] = mapped_column(String(100), nullable=True)
    selected_model: Mapped[str] = mapped_column(String(100), nullable=False)
    candidate_backends: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    routing_policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
