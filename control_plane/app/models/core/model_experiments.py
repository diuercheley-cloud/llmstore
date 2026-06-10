import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ModelExperiment(Base):
    __tablename__ = "model_experiments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|running|completed|rolled_back|promoted
    experiment_type: Mapped[str] = mapped_column(String(32), default="ab_test")  # ab_test|canary
    
    # Target criteria
    target_route_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    target_tenant_id: Mapped[str | None] = mapped_column(String(128), index=True)
    
    # Control logic
    auto_rollback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    error_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_threshold_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    variants = relationship("ModelExperimentVariant", back_populates="experiment", cascade="all, delete-orphan")
    assignments = relationship("ModelExperimentAssignment", back_populates="experiment", cascade="all, delete-orphan")
    metrics = relationship("ModelExperimentMetric", back_populates="experiment", cascade="all, delete-orphan")

class ModelExperimentVariant(Base):
    __tablename__ = "model_experiment_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False) # e.g. "A", "B", "canary"
    is_control: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Configuration to apply
    model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    backend_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    traffic_weight: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 to 100.0

    experiment = relationship("ModelExperiment", back_populates="variants")

class ModelExperimentAssignment(Base):
    __tablename__ = "model_experiment_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_experiment_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    experiment = relationship("ModelExperiment", back_populates="assignments")

class ModelExperimentMetric(Base):
    __tablename__ = "model_experiment_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_experiment_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False) # latency, cost, error_rate, eval_score
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    experiment = relationship("ModelExperiment", back_populates="metrics")
