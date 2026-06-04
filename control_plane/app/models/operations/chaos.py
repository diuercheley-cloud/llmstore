import uuid
from datetime import datetime

from app.db.base_class import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class ChaosExperiment(Base):
    __tablename__ = "chaos_experiments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True, unique=True)
    description = Column(Text)
    experiment_type = Column(String) # provider_timeout, redis_unavailable, etc.
    blast_radius = Column(String) # low, medium, high
    
    preconditions = Column(JSON, default=[])
    injection_config = Column(JSON, default={})
    expected_behavior = Column(Text)
    rollback_config = Column(JSON, default={})
    
    timeout_seconds = Column(Integer, default=60)
    safety_limits = Column(JSON, default={})
    tags = Column(JSON, default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    runs = relationship("ChaosRun", back_populates="experiment")

class ChaosRun(Base):
    __tablename__ = "chaos_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id = Column(String, ForeignKey("chaos_experiments.id"))
    status = Column(String, default="pending") # pending, running, completed, aborted, failed
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    operator_id = Column(String, nullable=True)
    environment = Column(String, default="test")
    
    results_json = Column(JSON, default={})
    error_message = Column(Text, nullable=True)
    
    experiment = relationship("ChaosExperiment", back_populates="runs")
    injections = relationship("ChaosInjection", back_populates="run")

class ChaosInjection(Base):
    __tablename__ = "chaos_injections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("chaos_runs.id"))
    injection_type = Column(String)
    target = Column(String)
    parameters = Column(JSON)
    
    injected_at = Column(DateTime, default=datetime.utcnow)
    rolled_back_at = Column(DateTime, nullable=True)
    
    run = relationship("ChaosRun", back_populates="injections")

class ChaosAssertion(Base):
    __tablename__ = "chaos_assertions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("chaos_runs.id"))
    name = Column(String)
    assertion_type = Column(String) # latency_threshold, error_rate, status_code
    condition = Column(String)
    result = Column(Boolean, nullable=True)
    actual_value = Column(String, nullable=True)

class ChaosReport(Base):
    __tablename__ = "chaos_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("chaos_runs.id"))
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    summary = Column(Text)
    resilience_score = Column(Float) # 0.0 to 1.0
    impact_analysis = Column(Text)
    recommendations = Column(JSON, default=[])
