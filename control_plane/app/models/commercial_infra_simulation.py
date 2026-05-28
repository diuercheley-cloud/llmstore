import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

class CommercialInfrastructureSimulation(Base):
    __tablename__ = "commercial_infra_simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # scale_up|scale_down|reroute|throttle|cache_expand|cluster_failover
    simulation_type = Column(String, index=True, nullable=False)
    # cluster|node|provider|model|qos_tier
    target_scope = Column(String, index=True, nullable=False)
    target_identifier = Column(String, index=True, nullable=False)
    
    requested_action_json = Column(JSON, nullable=False)
    predicted_capacity_impact_json = Column(JSON, nullable=True)
    predicted_cost_impact_brl = Column(Float, default=0.0)
    predicted_margin_impact_brl = Column(Float, default=0.0)
    predicted_sla_impact_json = Column(JSON, nullable=True)
    predicted_queue_impact_json = Column(JSON, nullable=True)
    predicted_latency_impact_json = Column(JSON, nullable=True)
    
    # low|medium|high|critical
    blast_radius = Column(String, index=True, default="low")
    
    # allowed|blocked|requires_approval
    safety_gate_status = Column(String, index=True, default="allowed")
    
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommercialSafetyPolicy(Base):
    __tablename__ = "commercial_safety_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name = Column(String, unique=True, index=True, nullable=False)
    enabled = Column(Boolean, default=True)
    
    max_predicted_cost_increase_percent = Column(Float, default=20.0)
    max_predicted_margin_drop_percent = Column(Float, default=10.0)
    max_predicted_sla_violation_percent = Column(Float, default=5.0)
    
    max_nodes_affected = Column(Integer, default=5)
    max_clusters_affected = Column(Integer, default=1)
    
    require_manual_approval_above_blast_radius = Column(String, default="medium")
    
    allow_scale_down = Column(Boolean, default=True)
    allow_scale_up = Column(Boolean, default=True)
    allow_cluster_failover = Column(Boolean, default=False)
    allow_cross_region_routing = Column(Boolean, default=False)
    
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommercialApprovalRecord(Base):
    __tablename__ = "commercial_approval_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("commercial_infra_simulations.id"), index=True, nullable=False)
    
    # pending|approved|rejected
    status = Column(String, index=True, default="pending")
    
    approver = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

class CommercialExecutionRecord(Base):
    __tablename__ = "commercial_infra_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("commercial_infra_simulations.id"), index=True, nullable=False)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("commercial_approval_records.id"), index=True, nullable=True)
    
    # kubernetes|nomad|mock
    adapter = Column(String, index=True, nullable=False)
    # scale_up|scale_down|reroute|...
    action_type = Column(String, index=True, nullable=False)
    
    target_scope = Column(String, index=True, nullable=False)
    target_identifier = Column(String, index=True, nullable=False)
    
    requested_action_json = Column(JSON, nullable=False)
    
    # pending|dry_run|executed|failed|blocked|rolled_back
    status = Column(String, index=True, default="pending")
    dry_run = Column(Boolean, default=True)
    
    leader_node_id = Column(String, nullable=True)
    fencing_token = Column(String, nullable=True)
    external_operation_id = Column(String, nullable=True)
    
    result_json = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

