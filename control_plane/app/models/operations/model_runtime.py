import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class ModelRuntimeInstance(Base):
    __tablename__ = "model_runtime_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False, index=True)
    backend_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("inference_backends.id"), nullable=False, index=True)
    model_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="loading", nullable=False)  # loading|ready|failed|unloading|stopped
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    health_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
