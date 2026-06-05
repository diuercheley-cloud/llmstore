import uuid
from datetime import datetime, UTC

from app.db.base import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text


class RuntimeBenchmarkRun(Base):
    __tablename__ = "runtime_benchmark_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    model_id = Column(String, index=True)
    profile_name = Column(String, nullable=True)
    
    # Metrics
    tokens_per_sec = Column(Float)
    latency_p50 = Column(Float)
    latency_p95 = Column(Float)
    latency_p99 = Column(Float)
    queue_wait_ms = Column(Float)
    gpu_memory_pressure = Column(Float)
    cpu_usage = Column(Float)
    cache_hit_ratio = Column(Float)
    fallback_rate = Column(Float)
    cost_per_1k_tokens = Column(Float)
    error_rate = Column(Float)
    
    metadata_json = Column(JSON, default={})

class RuntimeTuningProfile(Base):
    __tablename__ = "runtime_tuning_profiles"

    name = Column(String, primary_key=True) # balanced, low_latency, etc.
    description = Column(Text)
    config = Column(JSON) # e.g. {"max_concurrent_generations": 4, "response_cache_enabled": true}
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class RuntimeTuningRecommendation(Base):
    __tablename__ = "runtime_tuning_recommendations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    title = Column(String)
    description = Column(Text)
    action_type = Column(String) # CONFIG_UPDATE, SCALE_UP, etc.
    impact = Column(String) # PERFORMANCE, COST, STABILITY
    priority = Column(String) # low, medium, high, critical
    suggested_config = Column(JSON)
    status = Column(String, default="pending") # pending, applied, dismissed
    
    benchmark_run_id = Column(String, ForeignKey("runtime_benchmark_runs.id"), nullable=True)

class RuntimeTuningEvent(Base):
    __tablename__ = "runtime_tuning_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))
    event_type = Column(String) # PROFILE_APPLIED, PROFILE_ROLLBACK, RECOMMENDATION_DISMISSED
    profile_name = Column(String, nullable=True)
    previous_config = Column(JSON, nullable=True)
    new_config = Column(JSON, nullable=True)
    operator_id = Column(String, nullable=True)
    metadata_json = Column(JSON, default={})
