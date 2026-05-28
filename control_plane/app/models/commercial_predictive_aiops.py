import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey, Float
from app.db.base import Base

class CommercialFailurePrediction(Base):
    __tablename__ = "commercial_failure_predictions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, index=True)
    target_id = Column(String, index=True)  # node_id, workflow_id, etc.
    prediction_type = Column(String)  # queue_saturation, node_failure, quorum_loss
    confidence_score = Column(Float)
    predicted_failure_window_seconds = Column(Integer)
    details = Column(JSON)
    deterministic_hash = Column(String)
    immutable_hash = Column(String)
    sovereign_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialAnomalySignal(Base):
    __tablename__ = "commercial_anomaly_signals"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, index=True)
    source_id = Column(String, index=True)
    anomaly_type = Column(String)  # thermal, power, latency, drift
    severity = Column(String)  # info, warning, critical
    drift_probability = Column(Float)
    metrics_snapshot = Column(JSON)
    deterministic_hash = Column(String)
    immutable_hash = Column(String)
    signed_receipt_id = Column(String, nullable=True)
    sovereign_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialNodeHealthForecast(Base):
    __tablename__ = "commercial_node_health_forecasts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id = Column(String, index=True)
    health_score_trend = Column(JSON)  # List of (timestamp, score)
    predicted_status = Column(String)
    forecast_window_minutes = Column(Integer)
    risk_factors = Column(JSON)
    deterministic_hash = Column(String)
    immutable_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRuntimeRiskTrend(Base):
    __tablename__ = "commercial_runtime_risk_trends"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, index=True)
    risk_type = Column(String)  # operational, financial, technical
    risk_score = Column(Float)
    trend_direction = Column(String)  # up, down, stable
    contributing_events = Column(JSON)
    deterministic_hash = Column(String)
    immutable_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialAIOpsRecommendation(Base):
    __tablename__ = "commercial_aiops_recommendations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, index=True)
    action_type = Column(String)  # scale_up, isolate_node, throttle_tenant, etc.
    target_id = Column(String)
    priority = Column(String)  # low, medium, high, critical
    rationale = Column(JSON)
    mode = Column(String, default="advisory")  # advisory, dry_run, guarded_recovery
    status = Column(String, default="pending")  # pending, applied, dismissed
    deterministic_hash = Column(String)
    immutable_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
