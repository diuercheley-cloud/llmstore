from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.db.base import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID


class CommercialWorkflowDefinition(Base):
    __tablename__ = "commercial_workflow_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_name = Column(String(128), nullable=False)
    workflow_family = Column(String(128), nullable=True)
    client_id = Column(String(64), nullable=True, index=True)
    version = Column(Integer, default=1)
    steps_config = Column(JSON, nullable=False)
    dag_json = Column(JSON, nullable=True)
    entry_stage = Column(String(128), nullable=True)
    definition_hash = Column(String(64), nullable=True, index=True)
    immutable_hash = Column(String(64), nullable=True)
    policy_bundle_ref = Column(String(128), nullable=True)
    offline_compatible = Column(Boolean, default=True)
    sovereign_ready = Column(Boolean, default=True)
    is_deterministic = Column(Boolean, default=True)
    enforce_reproducibility = Column(Boolean, default=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class CommercialWorkflowExecution(Base):
    __tablename__ = "commercial_workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_definitions.id"), nullable=False
    )
    replay_of_execution_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_executions.id"), nullable=True
    )
    session_id = Column(String(128), nullable=True, index=True)
    request_id = Column(String(128), nullable=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="pending")
    execution_mode = Column(String(32), default="deterministic")
    execution_hash_chain = Column(String(128), nullable=True)
    dag_hash = Column(String(64), nullable=True)
    provenance_hash = Column(String(64), nullable=True)
    ledger_hash = Column(String(64), nullable=True)
    resume_token_hash = Column(String(64), nullable=True)
    last_checkpoint_hash = Column(String(64), nullable=True)
    current_step_index = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    policy_gate_status = Column(String(32), default="pending")
    determinism_status = Column(String(32), default="unknown")
    drift_detected = Column(Boolean, default=False)
    offline_bundle_hash = Column(String(64), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    governance_ledger_hash = Column(String(64), nullable=True)
    governance_status = Column(String(32), default="pending")
    replay_status = Column(String(32), default="not_started")
    confidential_metadata = Column(Boolean, default=False)


class CommercialWorkflowStage(Base):
    __tablename__ = "commercial_workflow_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    definition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_definitions.id"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    stage_key = Column(String(128), nullable=False, index=True)
    stage_name = Column(String(128), nullable=True)
    stage_type = Column(String(64), nullable=True)
    stage_order = Column(Integer, nullable=False, default=0)
    status = Column(String(32), default="pending")
    dependencies_json = Column(JSON, nullable=True)
    policy_gate_status = Column(String(32), default="pending")
    policy_decision_json = Column(JSON, nullable=True)
    planned_input_hash = Column(String(64), nullable=True)
    input_hash = Column(String(64), nullable=True)
    output_hash = Column(String(64), nullable=True)
    stage_hash = Column(String(64), nullable=True)
    previous_stage_hash = Column(String(64), nullable=True)
    lineage_hash = Column(String(64), nullable=True)
    checkpoint_hash = Column(String(64), nullable=True)
    receipt_hash = Column(String(64), nullable=True)
    runtime_snapshot_hash = Column(String(64), nullable=True)
    confidential_audit_hash = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    bound_policy_bundle_id = Column(UUID(as_uuid=True), nullable=True)
    active_policy_snapshot_id = Column(UUID(as_uuid=True), nullable=True)
    approval_required = Column(Boolean, default=False)
    approval_status = Column(String(32), default="not_required")
    governance_decision_signature = Column(String(255), nullable=True)
    governance_mode = Column(String(32), default="enforce")
    drift_status = Column(String(32), default="unknown")
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class CommercialWorkflowCheckpoint(Base):
    __tablename__ = "commercial_workflow_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    stage_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_stages.id"), nullable=True, index=True
    )
    step_index = Column(Integer, nullable=False)
    stage_key = Column(String(128), nullable=True, index=True)
    step_input_hash = Column(String(128), nullable=True)
    step_output_hash = Column(String(128), nullable=True)
    snapshot_hash = Column(String(64), nullable=True)
    previous_checkpoint_hash = Column(String(64), nullable=True)
    state_snapshot = Column(JSON, nullable=True)
    detached_signature = Column(String(255), nullable=True)
    signature_algorithm = Column(String(64), nullable=True)
    immutable_hash = Column(String(64), nullable=True)
    merkle_root = Column(String(128), nullable=True)
    replay_nonce = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class CommercialWorkflowReceipt(Base):
    __tablename__ = "commercial_workflow_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    receipt_hash = Column(String(64), nullable=False, index=True)
    previous_receipt_hash = Column(String(64), nullable=True)
    root_stage_hash = Column(String(64), nullable=True)
    root_checkpoint_hash = Column(String(64), nullable=True)
    provenance_hash = Column(String(64), nullable=True)
    detached_signature = Column(String(255), nullable=True)
    signature_algorithm = Column(String(64), nullable=True)
    verification_status = Column(String(32), default="pending")
    immutable_hash = Column(String(64), nullable=True)
    receipt_json = Column(JSON, nullable=True)
    export_classification = Column(String(32), default="sanitized")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    verified_at = Column(DateTime, nullable=True)


class CommercialWorkflowReplay(Base):
    __tablename__ = "commercial_workflow_replays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_execution_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_executions.id"), nullable=False
    )
    replay_execution_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_executions.id"), nullable=True
    )
    status = Column(String(32), default="pending")
    mismatched_step_index = Column(Integer, nullable=True)
    replay_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class CommercialWorkflowDeterminismReport(Base):
    __tablename__ = "commercial_workflow_determinism_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_executions.id"), nullable=False
    )
    determinism_score = Column(Float, default=1.0)
    drift_detected = Column(Boolean, default=False)
    drift_summary = Column(Text, nullable=True)
    verification_proof_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class CommercialWorkflowPolicyBinding(Base):
    __tablename__ = "commercial_workflow_policy_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    stage_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_stages.id"), nullable=False, index=True
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    bundle_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_policy_bundles.id"), nullable=True, index=True
    )
    bundle_ref = Column(String(128), nullable=True, index=True)
    binding_status = Column(String(32), default="pending", index=True)
    enforcement_mode = Column(String(32), default="enforce", nullable=False)
    runtime_policy_hash = Column(String(64), nullable=True, index=True)
    snapshot_hash = Column(String(64), nullable=True, index=True)
    rollback_from_binding_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_policy_bindings.id"), nullable=True
    )
    immutable_hash = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CommercialWorkflowPolicySnapshot(Base):
    __tablename__ = "commercial_workflow_policy_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    stage_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_stages.id"), nullable=False, index=True
    )
    binding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_policy_bindings.id"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    snapshot_type = Column(String(32), default="runtime", nullable=False)
    policy_hash = Column(String(64), nullable=False, index=True)
    runtime_context_hash = Column(String(64), nullable=True, index=True)
    snapshot_hash = Column(String(64), nullable=False, index=True)
    detached_signature = Column(String(255), nullable=True)
    signature_algorithm = Column(String(64), nullable=True)
    immutable_hash = Column(String(64), nullable=True, index=True)
    policy_json = Column(JSON, nullable=False)
    runtime_context_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CommercialWorkflowApproval(Base):
    __tablename__ = "commercial_workflow_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    stage_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_stages.id"), nullable=False, index=True
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    snapshot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_policy_snapshots.id"),
        nullable=True,
        index=True,
    )
    chain_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    step_index = Column(Integer, default=0, nullable=False)
    requested_by = Column(String(255), nullable=True)
    approver = Column(String(255), nullable=True)
    delegated_by = Column(String(255), nullable=True)
    decision_notes = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    expired_at = Column(DateTime, nullable=True)
    emergency_override = Column(Boolean, default=False)
    replay_safe = Column(Boolean, default=True)
    previous_decision_hash = Column(String(64), nullable=True)
    decision_hash = Column(String(64), nullable=False, index=True)
    detached_signature = Column(String(255), nullable=True)
    signature_algorithm = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CommercialWorkflowGovernanceEvent(Base):
    __tablename__ = "commercial_workflow_governance_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    stage_id = Column(
        UUID(as_uuid=True), ForeignKey("commercial_workflow_stages.id"), nullable=True, index=True
    )
    replay_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_replay_sessions.id"),
        nullable=True,
        index=True,
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(255), nullable=True)
    actor_metadata_json = Column(JSON, nullable=True)
    event_summary = Column(Text, nullable=True)
    event_payload_json = Column(JSON, nullable=True)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False, index=True)
    ledger_hash = Column(String(64), nullable=False, index=True)
    detached_signature = Column(String(255), nullable=True)
    signature_algorithm = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CommercialWorkflowReplaySession(Base):
    __tablename__ = "commercial_workflow_replay_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    replay_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=True,
        index=True,
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    session_status = Column(String(32), default="pending", nullable=False, index=True)
    requested_by = Column(String(255), nullable=True)
    deterministic_snapshot_hash = Column(String(64), nullable=True, index=True)
    comparison_hash = Column(String(64), nullable=True, index=True)
    report_hash = Column(String(64), nullable=True, index=True)
    report_signature = Column(String(255), nullable=True)
    mismatch_detected = Column(Boolean, default=False)
    policy_mismatch_detected = Column(Boolean, default=False)
    drift_score = Column(Float, nullable=True)
    replay_report_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    completed_at = Column(DateTime, nullable=True)
