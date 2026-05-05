import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class ModelBackendRoute(Base):
    __tablename__ = "model_backend_routes"
    __table_args__ = (
        UniqueConstraint("model_registry_id", "inference_backend_id", name="uq_model_backend_route"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_registry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inference_backend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inference_backends.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="healthy", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    model = relationship("ModelRegistry", back_populates="backend_routes")
    inference_backend = relationship("InferenceBackend", back_populates="model_routes")
