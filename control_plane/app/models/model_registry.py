import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    model_alias: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    inference_backend_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("inference_backends.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="llama.cpp", nullable=False)
    model_file: Mapped[str] = mapped_column(String(255), nullable=False)
    context_length: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="configured", nullable=False)
    prompt_template: Mapped[str | None] = mapped_column(Text(), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    inference_backend = relationship("InferenceBackend", back_populates="models")
    backend_routes = relationship("ModelBackendRoute", back_populates="model", cascade="all, delete-orphan")
