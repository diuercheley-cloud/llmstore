import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey, Float
from app.db.base import Base

class CommercialRuntimeFabricEvent(Base):
    __tablename__ = "commercial_runtime_fabric_events"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, index=True) # failure_detected, recovery_initiated, healing_completed, drift_detected
    severity = Column(String) # info, warning, critical
    source_node_id = Column(String, index=True)
    component = Column(String) # workflow, mesh, governance, runtime
    details = Column(JSON)
    signature = Column(String) # for auditability
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialRuntimeRecoveryPlan(Base):
    __tablename__ = "commercial_runtime_recovery_plans"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("commercial_runtime_fabric_events.id"))
    mode = Column(String) # advisory, dry_run, guarded_recovery, sovereign_safe_mode
    status = Column(String, default="pending") # pending, executing, completed, failed, cancelled
    steps = Column(JSON) # ordered list of healing actions
    approved_by = Column(String, nullable=True) # governance supervisor ID or admin
    execution_log = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialRuntimeHealingAction(Base):
    __tablename__ = "commercial_runtime_healing_actions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String, ForeignKey("commercial_runtime_recovery_plans.id"))
    action_type = Column(String) # restart_service, rollback_state, replay_workflow, isolate_node, resync_mesh
    target_id = Column(String) # node_id, workflow_id, etc.
    parameters = Column(JSON)
    status = Column(String, default="pending")
    result = Column(JSON, nullable=True)
    signed_receipt = Column(String, nullable=True) # proof of execution
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

class CommercialRuntimeFabricHealth(Base):
    __tablename__ = "commercial_runtime_fabric_health"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    node_id = Column(String, index=True)
    status = Column(String) # healthy, degraded, critical, isolated
    metrics = Column(JSON) # cpu, mem, latency, drift_factor
    last_check = Column(DateTime, default=datetime.utcnow)
    quarum_status = Column(Boolean, default=True)
    degraded_mode_active = Column(Boolean, default=False)

class CommercialRuntimeDeterminismDrift(Base):
    __tablename__ = "commercial_runtime_determinism_drift"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, index=True)
    step_index = Column(Integer)
    expected_hash = Column(String)
    actual_hash = Column(String)
    drift_details = Column(JSON)
    detected_at = Column(DateTime, default=datetime.utcnow)
    repaired_at = Column(DateTime, nullable=True)
    repair_plan_id = Column(String, ForeignKey("commercial_runtime_recovery_plans.id"), nullable=True)
