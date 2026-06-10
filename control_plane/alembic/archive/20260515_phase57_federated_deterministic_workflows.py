"""phase57_federated_deterministic_workflows

Revision ID: 20260515_phase57
Revises: 20260515_phase56
Create Date: 2026-05-15 23:20:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_phase57"
down_revision = "20260515_phase56"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def _uuid_type():
    return postgresql.UUID(as_uuid=True) if _dialect_name() == "postgresql" else sa.String(length=36)


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if _dialect_name() == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "commercial_federated_workflow_executions",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("workflow_execution_id", _uuid_type(), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("execution_hash", sa.String(length=64), nullable=False),
        sa.Column("dag_hash", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("consensus_status", sa.String(length=32), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False),
        sa.Column("federation_mode", sa.String(length=32), nullable=False),
        sa.Column("deterministic_clock", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_execution_receipt", sa.Text(), nullable=True),
        sa.Column("attestation_summary", _json_type(), nullable=True),
        sa.Column("sovereign_mode", sa.String(length=32), nullable=False),
        sa.Column("enforcement_hash", sa.String(length=64), nullable=True),
        sa.Column("governance_decision_trail_json", _json_type(), nullable=True),
        sa.Column("stage_ownership_json", _json_type(), nullable=True),
        sa.Column("dag_partition_json", _json_type(), nullable=True),
        sa.Column("runtime_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("routing_decision_hash", sa.String(length=64), nullable=True),
        sa.Column("reconciliation_status", sa.String(length=32), nullable=False),
        sa.Column("drift_detected", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["commercial_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_execution_id", "region_id", "cluster_id", name="uq_fed_workflow_exec_region_cluster"),
    )
    op.create_index("ix_fed_workflow_exec_lookup", "commercial_federated_workflow_executions", ["tenant_id", "workflow_id", "cluster_id"], unique=False)
    op.create_index("ix_fed_workflow_exec_status", "commercial_federated_workflow_executions", ["consensus_status", "replay_status", "federation_mode"], unique=False)
    op.create_index("ix_fed_workflow_exec_chain", "commercial_federated_workflow_executions", ["immutable_hash", "previous_hash"], unique=False)

    op.create_table(
        "commercial_workflow_execution_peers",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("federated_execution_id", _uuid_type(), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("peer_region_id", sa.String(length=64), nullable=False),
        sa.Column("peer_cluster_id", sa.String(length=128), nullable=False),
        sa.Column("execution_hash", sa.String(length=64), nullable=True),
        sa.Column("dag_hash", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("consensus_status", sa.String(length=32), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False),
        sa.Column("federation_mode", sa.String(length=32), nullable=False),
        sa.Column("deterministic_clock", sa.String(length=64), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_execution_receipt", sa.Text(), nullable=True),
        sa.Column("attestation_summary", _json_type(), nullable=True),
        sa.Column("sovereign_mode", sa.String(length=32), nullable=False),
        sa.Column("trust_status", sa.String(length=32), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["federated_execution_id"], ["commercial_federated_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("federated_execution_id", "peer_cluster_id", name="uq_fed_workflow_peer_cluster"),
    )
    op.create_index("ix_fed_workflow_peer_scope", "commercial_workflow_execution_peers", ["tenant_id", "peer_cluster_id", "trust_status"], unique=False)
    op.create_index("ix_fed_workflow_peer_chain", "commercial_workflow_execution_peers", ["immutable_hash", "previous_hash"], unique=False)

    op.create_table(
        "commercial_workflow_execution_leases",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("federated_execution_id", _uuid_type(), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("execution_hash", sa.String(length=64), nullable=False),
        sa.Column("dag_hash", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=False),
        sa.Column("lease_token", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consensus_status", sa.String(length=32), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False),
        sa.Column("federation_mode", sa.String(length=32), nullable=False),
        sa.Column("deterministic_clock", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_execution_receipt", sa.Text(), nullable=True),
        sa.Column("attestation_summary", _json_type(), nullable=True),
        sa.Column("sovereign_mode", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["federated_execution_id"], ["commercial_federated_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fed_workflow_leases_active", "commercial_workflow_execution_leases", ["federated_execution_id", "status", "expires_at"], unique=False)
    op.create_index("ix_fed_workflow_leases_owner", "commercial_workflow_execution_leases", ["lease_owner", "cluster_id", "status"], unique=False)
    op.create_index("ix_fed_workflow_leases_chain", "commercial_workflow_execution_leases", ["immutable_hash", "previous_hash"], unique=False)

    op.create_table(
        "commercial_workflow_consensus_events",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("federated_execution_id", _uuid_type(), nullable=False),
        sa.Column("peer_id", _uuid_type(), nullable=True),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("execution_hash", sa.String(length=64), nullable=False),
        sa.Column("dag_hash", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("consensus_status", sa.String(length=32), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False),
        sa.Column("federation_mode", sa.String(length=32), nullable=False),
        sa.Column("deterministic_clock", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_execution_receipt", sa.Text(), nullable=True),
        sa.Column("attestation_summary", _json_type(), nullable=True),
        sa.Column("sovereign_mode", sa.String(length=32), nullable=False),
        sa.Column("quorum_size", sa.Integer(), nullable=False),
        sa.Column("quorum_threshold", sa.Integer(), nullable=False),
        sa.Column("event_payload_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["federated_execution_id"], ["commercial_federated_workflow_executions.id"]),
        sa.ForeignKeyConstraint(["peer_id"], ["commercial_workflow_execution_peers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fed_workflow_consensus_scope", "commercial_workflow_consensus_events", ["federated_execution_id", "event_type", "created_at"], unique=False)
    op.create_index("ix_fed_workflow_consensus_chain", "commercial_workflow_consensus_events", ["immutable_hash", "previous_hash"], unique=False)

    op.create_table(
        "commercial_workflow_replay_federation_reports",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("federated_execution_id", _uuid_type(), nullable=False),
        sa.Column("source_execution_id", _uuid_type(), nullable=False),
        sa.Column("workflow_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("execution_hash", sa.String(length=64), nullable=False),
        sa.Column("dag_hash", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("consensus_status", sa.String(length=32), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False),
        sa.Column("federation_mode", sa.String(length=32), nullable=False),
        sa.Column("deterministic_clock", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_execution_receipt", sa.Text(), nullable=True),
        sa.Column("attestation_summary", _json_type(), nullable=True),
        sa.Column("sovereign_mode", sa.String(length=32), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("mismatch_detected", sa.Boolean(), nullable=False),
        sa.Column("replay_report_json", _json_type(), nullable=True),
        sa.Column("report_signature", sa.Text(), nullable=True),
        sa.Column("report_bundle_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["federated_execution_id"], ["commercial_federated_workflow_executions.id"]),
        sa.ForeignKeyConstraint(["source_execution_id"], ["commercial_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fed_workflow_replay_scope", "commercial_workflow_replay_federation_reports", ["federated_execution_id", "replay_status", "created_at"], unique=False)
    op.create_index("ix_fed_workflow_replay_chain", "commercial_workflow_replay_federation_reports", ["immutable_hash", "previous_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fed_workflow_replay_chain", table_name="commercial_workflow_replay_federation_reports")
    op.drop_index("ix_fed_workflow_replay_scope", table_name="commercial_workflow_replay_federation_reports")
    op.drop_table("commercial_workflow_replay_federation_reports")
    op.drop_index("ix_fed_workflow_consensus_chain", table_name="commercial_workflow_consensus_events")
    op.drop_index("ix_fed_workflow_consensus_scope", table_name="commercial_workflow_consensus_events")
    op.drop_table("commercial_workflow_consensus_events")
    op.drop_index("ix_fed_workflow_leases_chain", table_name="commercial_workflow_execution_leases")
    op.drop_index("ix_fed_workflow_leases_owner", table_name="commercial_workflow_execution_leases")
    op.drop_index("ix_fed_workflow_leases_active", table_name="commercial_workflow_execution_leases")
    op.drop_table("commercial_workflow_execution_leases")
    op.drop_index("ix_fed_workflow_peer_chain", table_name="commercial_workflow_execution_peers")
    op.drop_index("ix_fed_workflow_peer_scope", table_name="commercial_workflow_execution_peers")
    op.drop_table("commercial_workflow_execution_peers")
    op.drop_index("ix_fed_workflow_exec_chain", table_name="commercial_federated_workflow_executions")
    op.drop_index("ix_fed_workflow_exec_status", table_name="commercial_federated_workflow_executions")
    op.drop_index("ix_fed_workflow_exec_lookup", table_name="commercial_federated_workflow_executions")
    op.drop_table("commercial_federated_workflow_executions")
