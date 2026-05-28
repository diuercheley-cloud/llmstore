from sqlalchemy import Column, String, Boolean, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base import Base

class CommercialGlobalTrafficPolicy(Base):
    __tablename__ = "commercial_global_traffic_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    enabled = Column(Boolean, default=False)
    source_cluster_id = Column(String, nullable=False)
    target_cluster_id = Column(String, nullable=False)
    tenant_id = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    region = Column(String, nullable=True)
    mode = Column(String, nullable=False) # dry_run, canary
    traffic_percent = Column(Integer, nullable=False)
    max_traffic_percent = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending") # pending, active, paused, rolled_back, completed
    reason = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)

class CommercialGlobalTrafficDecision(Base):
    __tablename__ = "commercial_global_traffic_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    client_id = Column(String, nullable=True)
    tenant_id = Column(String, nullable=True)
    selected_cluster_id = Column(String, nullable=False)
    original_cluster_id = Column(String, nullable=False)
    target_cluster_id = Column(String, nullable=True)
    decision = Column(String, nullable=False) # stay_local, shift_to_target, rejected, dry_run_would_shift
    bucket = Column(Integer, nullable=False)
    traffic_percent = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
