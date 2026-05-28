import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.time import utc_now

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")

class GpuDevice(Base):
    __tablename__ = "gpu_devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runtime_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False, index=True)
    gpu_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    memory_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    memory_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    utilization_percent: Mapped[float] = mapped_column(Float, default=0.0)
    temperature_c: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="active") # active, degraded, offline
    
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class GpuAllocation(Base):
    __tablename__ = "gpu_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gpu_device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gpu_devices.id"), nullable=False, index=True)
    model_registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False)
    allocated_memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="allocated") # allocated, releasing, released
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class GpuCapacitySnapshot(Base):
    __tablename__ = "gpu_capacity_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runtime_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False, index=True)
    total_memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    used_memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_utilization_percent: Mapped[float] = mapped_column(Float, nullable=False)
    gpu_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AutoscalingPolicy(Base):
    __tablename__ = "autoscaling_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_registry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), default="queue_depth") # queue_depth, latency_p95, gpu_pressure
    min_replicas: Mapped[int] = mapped_column(Integer, default=1)
    max_replicas: Mapped[int] = mapped_column(Integer, default=5)
    target_value: Mapped[float] = mapped_column(Float, nullable=False) # e.g. target queue depth or latency
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mode: Mapped[str] = mapped_column(String(32), default="recommendation") # recommendation, active
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class AutoscalingEvent(Base):
    __tablename__ = "autoscaling_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("autoscaling_policies.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32)) # scale_up, scale_down, no_op
    reason: Mapped[str] = mapped_column(String(1024))
    replicas_before: Mapped[int] = mapped_column(Integer)
    replicas_after: Mapped[int] = mapped_column(Integer)
    metrics_snapshot: Mapped[dict] = mapped_column(JSON_DOCUMENT, default={})
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
