import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.time import utc_now

class RuntimeNode(Base):
    __tablename__ = "runtime_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    node_type: Mapped[str] = mapped_column(String(32), default="local") # local|remote|kubernetes|edge
    gpu_count: Mapped[int] = mapped_column(Integer, default=0)
    gpu_memory_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    memory_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="registering") # registering|ready|degraded|offline|draining
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default={})
    trust_level: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class RuntimeNodeHeartbeat(Base):
    __tablename__ = "runtime_node_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False, index=True)
    cpu_usage_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage_mb: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_usage_percent: Mapped[dict] = mapped_column(JSON, default={}) # List/Dict of percentages
    active_requests: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default={})
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RuntimeModelPlacement(Base):
    __tablename__ = "runtime_model_placements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False, index=True)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="loading") # loading, ready, error
    last_error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class RuntimeRoutingEvent(Base):
    __tablename__ = "runtime_routing_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(255), index=True)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False)
    selected_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False)
    routing_strategy: Mapped[str] = mapped_column(String(32)) # round_robin, least_load, gpu_priority
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class RuntimeFailoverEvent(Base):
    __tablename__ = "runtime_failover_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(255), index=True)
    failed_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False)
    target_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runtime_nodes.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(1024))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
