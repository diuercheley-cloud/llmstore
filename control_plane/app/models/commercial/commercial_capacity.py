import uuid
from datetime import datetime, UTC

from app.db.base import Base
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID


class CommercialCapacitySnapshot(Base):
    __tablename__ = "commercial_capacity_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String, index=True, nullable=False)
    node_id = Column(String, index=True, nullable=True)
    provider = Column(String, index=True, nullable=True)
    model = Column(String, index=True, nullable=True)
    qos_tier = Column(String, index=True, nullable=True)
    timestamp = Column(DateTime, index=True, default=lambda: datetime.now(UTC))
    
    requests_per_minute = Column(Float, default=0.0)
    concurrent_requests = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    p95_latency_ms = Column(Float, default=0.0)
    queue_depth = Column(Integer, default=0)
    
    gpu_utilization = Column(Float, nullable=True)
    cpu_utilization = Column(Float, nullable=True)
    memory_utilization = Column(Float, nullable=True)
    estimated_tokens_per_second = Column(Float, nullable=True)
    
    sla_violation_rate = Column(Float, default=0.0)
    fallback_rate = Column(Float, default=0.0)
    block_rate = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialCapacityForecast(Base):
    __tablename__ = "commercial_capacity_forecasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String, index=True, nullable=False)
    provider = Column(String, index=True, nullable=True)
    model = Column(String, index=True, nullable=True)
    qos_tier = Column(String, index=True, nullable=True)
    
    forecast_window_minutes = Column(Integer, default=60)
    predicted_rpm = Column(Float, default=0.0)
    predicted_concurrency = Column(Float, default=0.0)
    predicted_latency_ms = Column(Float, default=0.0)
    predicted_queue_depth = Column(Float, default=0.0)
    predicted_sla_violation_rate = Column(Float, default=0.0)
    
    predicted_capacity_exhaustion_at = Column(DateTime, nullable=True)
    recommended_action = Column(String, nullable=True)
    confidence = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialAutoscalingRecommendation(Base):
    __tablename__ = "commercial_autoscaling_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String, index=True, nullable=False)
    
    # scale_up|scale_down|rebalance|reroute|throttle|cache_more
    recommendation_type = Column(String, index=True, nullable=False)
    
    # cluster|provider|model|qos_tier
    target_scope = Column(String, index=True, nullable=False)
    target_identifier = Column(String, index=True, nullable=False)
    
    reason = Column(String, nullable=False)
    predicted_sla_risk = Column(Float, default=0.0)
    estimated_cost_impact_brl = Column(Float, default=0.0)
    estimated_margin_impact_brl = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    dry_run_only = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
