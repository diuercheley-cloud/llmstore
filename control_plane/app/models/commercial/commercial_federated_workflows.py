from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.db.base import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID


class CommercialFederatedWorkflowExecution(Base):
    __tablename__ = "commercial_federated_workflow_executions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_execution_id",
            "region_id",
            "cluster_id",
            name="uq_fed_workflow_exec_region_cluster",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    region_id = Column(String(64), nullable=False, index=True)
    cluster_id = Column(String(128), nullable=False, index=True)
    execution_hash = Column(String(64), nullable=False, index=True)
    dag_hash = Column(String(64), nullable=True, index=True)
    provenance_hash = Column(String(64), nullable=True, index=True)
    lease_owner = Column(String(128), nullable=True, index=True)
    consensus_status = Column(String(32), default="pending", nullable=False, index=True)
    replay_status = Column(String(32), default="not_started", nullable=False, index=True)
    federation_mode = Column(String(32), default="local_only", nullable=False, index=True)
    deterministic_clock = Column(String(64), nullable=False, index=True)
    immutable_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=True, index=True)
    signed_execution_receipt = Column(Text, nullable=True)
    attestation_summary = Column(JSON, nullable=True)
    sovereign_mode = Column(String(32), default="disabled", nullable=False, index=True)
    enforcement_hash = Column(String(64), nullable=True, index=True)
    governance_decision_trail_json = Column(JSON, nullable=True)
    stage_ownership_json = Column(JSON, nullable=True)
    dag_partition_json = Column(JSON, nullable=True)
    runtime_snapshot_hash = Column(String(64), nullable=True, index=True)
    routing_decision_hash = Column(String(64), nullable=True, index=True)
    reconciliation_status = Column(String(32), default="clean", nullable=False, index=True)
    drift_detected = Column(Boolean, default=False, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), index=True
    )


class CommercialWorkflowExecutionPeer(Base):
    __tablename__ = "commercial_workflow_execution_peers"
    __table_args__ = (
        UniqueConstraint(
            "federated_execution_id", "peer_cluster_id", name="uq_fed_workflow_peer_cluster"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    federated_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_federated_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    region_id = Column(String(64), nullable=False, index=True)
    cluster_id = Column(String(128), nullable=False, index=True)
    peer_region_id = Column(String(64), nullable=False, index=True)
    peer_cluster_id = Column(String(128), nullable=False, index=True)
    execution_hash = Column(String(64), nullable=True, index=True)
    dag_hash = Column(String(64), nullable=True, index=True)
    provenance_hash = Column(String(64), nullable=True, index=True)
    lease_owner = Column(String(128), nullable=True, index=True)
    consensus_status = Column(String(32), default="pending", nullable=False, index=True)
    replay_status = Column(String(32), default="not_started", nullable=False, index=True)
    federation_mode = Column(String(32), default="local_only", nullable=False, index=True)
    deterministic_clock = Column(String(64), nullable=True, index=True)
    immutable_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=True, index=True)
    signed_execution_receipt = Column(Text, nullable=True)
    attestation_summary = Column(JSON, nullable=True)
    sovereign_mode = Column(String(32), default="disabled", nullable=False, index=True)
    trust_status = Column(String(32), default="trusted", nullable=False, index=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), index=True
    )


class CommercialWorkflowExecutionLease(Base):
    __tablename__ = "commercial_workflow_execution_leases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    federated_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_federated_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    region_id = Column(String(64), nullable=False, index=True)
    cluster_id = Column(String(128), nullable=False, index=True)
    execution_hash = Column(String(64), nullable=False, index=True)
    dag_hash = Column(String(64), nullable=True, index=True)
    provenance_hash = Column(String(64), nullable=True, index=True)
    lease_owner = Column(String(128), nullable=False, index=True)
    lease_token = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default="active", nullable=False, index=True)
    consensus_status = Column(String(32), default="pending", nullable=False, index=True)
    replay_status = Column(String(32), default="not_started", nullable=False, index=True)
    federation_mode = Column(String(32), default="local_only", nullable=False, index=True)
    deterministic_clock = Column(String(64), nullable=False, index=True)
    immutable_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=True, index=True)
    signed_execution_receipt = Column(Text, nullable=True)
    attestation_summary = Column(JSON, nullable=True)
    sovereign_mode = Column(String(32), default="disabled", nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    renewed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CommercialWorkflowConsensusEvent(Base):
    __tablename__ = "commercial_workflow_consensus_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    federated_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_federated_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    peer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_execution_peers.id"),
        nullable=True,
        index=True,
    )
    workflow_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    region_id = Column(String(64), nullable=False, index=True)
    cluster_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    execution_hash = Column(String(64), nullable=False, index=True)
    dag_hash = Column(String(64), nullable=True, index=True)
    provenance_hash = Column(String(64), nullable=True, index=True)
    lease_owner = Column(String(128), nullable=True, index=True)
    consensus_status = Column(String(32), default="pending", nullable=False, index=True)
    replay_status = Column(String(32), default="not_started", nullable=False, index=True)
    federation_mode = Column(String(32), default="local_only", nullable=False, index=True)
    deterministic_clock = Column(String(64), nullable=False, index=True)
    immutable_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=True, index=True)
    signed_execution_receipt = Column(Text, nullable=True)
    attestation_summary = Column(JSON, nullable=True)
    sovereign_mode = Column(String(32), default="disabled", nullable=False, index=True)
    quorum_size = Column(Integer, default=0, nullable=False)
    quorum_threshold = Column(Integer, default=0, nullable=False)
    event_payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CommercialWorkflowReplayFederationReport(Base):
    __tablename__ = "commercial_workflow_replay_federation_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    federated_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_federated_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    source_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("commercial_workflow_executions.id"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    region_id = Column(String(64), nullable=False, index=True)
    cluster_id = Column(String(128), nullable=False, index=True)
    execution_hash = Column(String(64), nullable=False, index=True)
    dag_hash = Column(String(64), nullable=True, index=True)
    provenance_hash = Column(String(64), nullable=True, index=True)
    lease_owner = Column(String(128), nullable=True, index=True)
    consensus_status = Column(String(32), default="pending", nullable=False, index=True)
    replay_status = Column(String(32), default="pending", nullable=False, index=True)
    federation_mode = Column(String(32), default="local_only", nullable=False, index=True)
    deterministic_clock = Column(String(64), nullable=False, index=True)
    immutable_hash = Column(String(64), nullable=False, index=True)
    previous_hash = Column(String(64), nullable=True, index=True)
    signed_execution_receipt = Column(Text, nullable=True)
    attestation_summary = Column(JSON, nullable=True)
    sovereign_mode = Column(String(32), default="disabled", nullable=False, index=True)
    drift_score = Column(Float, default=0.0, nullable=False)
    mismatch_detected = Column(Boolean, default=False, nullable=False)
    replay_report_json = Column(JSON, nullable=True)
    report_signature = Column(Text, nullable=True)
    report_bundle_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
