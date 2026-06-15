import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class InferenceBackend(Base):
    __tablename__ = "inference_backends"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    backend_url: Mapped[str] = mapped_column(String(255), nullable=False)
    healthcheck_path: Mapped[str] = mapped_column(String(64), default="/health", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="configured", nullable=False)
    max_parallel_requests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_running: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    models = relationship("ModelRegistry", back_populates="inference_backend")
    model_routes = relationship(
        "ModelBackendRoute", back_populates="inference_backend", cascade="all, delete-orphan"
    )
    generation_jobs = relationship("GenerationJob", back_populates="inference_backend")
