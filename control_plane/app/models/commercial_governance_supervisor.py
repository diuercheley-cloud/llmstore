import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class CommercialGovernanceSupervisorPolicy(Base):
    __tablename__ = "commercial_governance_supervisor_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # drift, financial, compliance, fairness, qos, confidentiality
    
    rules: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    mode: Mapped[str] = mapped_column(String(32), default="advisory", nullable=False)
    # advisory, dry_run, guarded_enforce, sovereign_restricted
    
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class CommercialGovernanceSupervisorRiskScore(Base):
    __tablename__ = "commercial_governance_supervisor_risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    
    overall_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    financial_risk: Mapped[float] = mapped_column(Float, default=0.0)
    compliance_risk: Mapped[float] = mapped_column(Float, default=0.0)
    qos_risk: Mapped[float] = mapped_column(Float, default=0.0)
    security_risk: Mapped[float] = mapped_column(Float, default=0.0)
    
    risk_factors: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class CommercialGovernanceSupervisorIncident(Base):
    __tablename__ = "commercial_governance_supervisor_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False) # low, medium, high, critical
    
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    triggering_signals: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    correlated_anomalies: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    # open, investigating, resolved, false_positive
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialGovernanceSupervisorDecision(Base):
    __tablename__ = "commercial_governance_supervisor_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_governance_supervisor_incidents.id", ondelete="CASCADE"), nullable=True, index=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_governance_supervisor_policies.id", ondelete="SET NULL"), nullable=True)
    
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    mode_used: Mapped[str] = mapped_column(String(32), nullable=False) # advisory, dry_run, guarded_enforce, sovereign_restricted
    
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CommercialGovernanceSupervisorAction(Base):
    __tablename__ = "commercial_governance_supervisor_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_governance_supervisor_decisions.id", ondelete="CASCADE"), index=True)
    
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # throttle, quarantine, pause_workflow, block_runtime, re_attest, reroute, safe_mode
    
    target_resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending, executing, completed, failed, rolled_back
    
    execution_result: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    rollback_hook: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
