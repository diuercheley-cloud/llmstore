"""phase56_workflow_policy_enforcement

Revision ID: 20260515_phase56
Revises: 20260515_phase55
Create Date: 2026-05-15 21:45:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_phase56"
down_revision = "20260515_phase55"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def _uuid_type():
    return (
        postgresql.UUID(as_uuid=True) if _dialect_name() == "postgresql" else sa.String(length=36)
    )


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if _dialect_name() == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("governance_ledger_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("governance_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("replay_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("confidential_metadata", sa.Boolean(), nullable=True),
    )
    op.create_index(
        "ix_commercial_workflow_executions_governance_status",
        "commercial_workflow_executions",
        ["tenant_id", "governance_status"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_executions_replay_status",
        "commercial_workflow_executions",
        ["tenant_id", "replay_status"],
        unique=False,
    )

    op.add_column(
        "commercial_workflow_stages",
        sa.Column("bound_policy_bundle_id", _uuid_type(), nullable=True),
    )
    op.add_column(
        "commercial_workflow_stages",
        sa.Column("active_policy_snapshot_id", _uuid_type(), nullable=True),
    )
    op.add_column(
        "commercial_workflow_stages", sa.Column("approval_required", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "commercial_workflow_stages",
        sa.Column("approval_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_stages",
        sa.Column("governance_decision_signature", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "commercial_workflow_stages",
        sa.Column("governance_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_stages", sa.Column("drift_status", sa.String(length=32), nullable=True)
    )
    op.create_foreign_key(
        "fk_workflow_stages_bound_policy_bundle",
        "commercial_workflow_stages",
        "commercial_policy_bundles",
        ["bound_policy_bundle_id"],
        ["id"],
    )

    op.create_table(
        "commercial_workflow_policy_bindings",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("stage_id", _uuid_type(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("bundle_id", _uuid_type(), nullable=True),
        sa.Column("bundle_ref", sa.String(length=128), nullable=True),
        sa.Column("binding_status", sa.String(length=32), nullable=False),
        sa.Column("enforcement_mode", sa.String(length=32), nullable=False),
        sa.Column("runtime_policy_hash", sa.String(length=64), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("rollback_from_binding_id", _uuid_type(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["commercial_policy_bundles.id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_workflow_executions.id"]),
        sa.ForeignKeyConstraint(
            ["rollback_from_binding_id"], ["commercial_workflow_policy_bindings.id"]
        ),
        sa.ForeignKeyConstraint(["stage_id"], ["commercial_workflow_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_workflow_policy_bindings_exec_stage",
        "commercial_workflow_policy_bindings",
        ["execution_id", "stage_id"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_policy_bindings_tenant_status",
        "commercial_workflow_policy_bindings",
        ["tenant_id", "binding_status"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_policy_bindings_runtime_hash",
        "commercial_workflow_policy_bindings",
        ["runtime_policy_hash"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_policy_bindings_snapshot_hash",
        "commercial_workflow_policy_bindings",
        ["snapshot_hash"],
        unique=False,
    )

    op.create_table(
        "commercial_workflow_policy_snapshots",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("stage_id", _uuid_type(), nullable=False),
        sa.Column("binding_id", _uuid_type(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False),
        sa.Column("policy_hash", sa.String(length=64), nullable=False),
        sa.Column("runtime_context_hash", sa.String(length=64), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("detached_signature", sa.String(length=255), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=True),
        sa.Column("policy_json", _json_type(), nullable=False),
        sa.Column("runtime_context_json", _json_type(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["binding_id"], ["commercial_workflow_policy_bindings.id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_workflow_executions.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["commercial_workflow_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_workflow_policy_snapshots_exec_stage",
        "commercial_workflow_policy_snapshots",
        ["execution_id", "stage_id"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_policy_snapshots_tenant_hash",
        "commercial_workflow_policy_snapshots",
        ["tenant_id", "snapshot_hash"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_policy_snapshots_policy_hash",
        "commercial_workflow_policy_snapshots",
        ["policy_hash"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_policy_snapshots_runtime_hash",
        "commercial_workflow_policy_snapshots",
        ["runtime_context_hash"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_workflow_stages_policy_snapshot",
        "commercial_workflow_stages",
        "commercial_workflow_policy_snapshots",
        ["active_policy_snapshot_id"],
        ["id"],
    )

    op.create_table(
        "commercial_workflow_approvals",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("stage_id", _uuid_type(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_id", _uuid_type(), nullable=True),
        sa.Column("chain_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("approver", sa.String(length=255), nullable=True),
        sa.Column("delegated_by", sa.String(length=255), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emergency_override", sa.Boolean(), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("previous_decision_hash", sa.String(length=64), nullable=True),
        sa.Column("decision_hash", sa.String(length=64), nullable=False),
        sa.Column("detached_signature", sa.String(length=255), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_workflow_executions.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["commercial_workflow_policy_snapshots.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["commercial_workflow_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_workflow_approvals_chain",
        "commercial_workflow_approvals",
        ["chain_id", "step_index"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_approvals_tenant_status",
        "commercial_workflow_approvals",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_approvals_expires",
        "commercial_workflow_approvals",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_approvals_decision_hash",
        "commercial_workflow_approvals",
        ["decision_hash"],
        unique=False,
    )

    op.create_table(
        "commercial_workflow_replay_sessions",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("original_execution_id", _uuid_type(), nullable=False),
        sa.Column("replay_execution_id", _uuid_type(), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("session_status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("deterministic_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("comparison_hash", sa.String(length=64), nullable=True),
        sa.Column("report_hash", sa.String(length=64), nullable=True),
        sa.Column("report_signature", sa.String(length=255), nullable=True),
        sa.Column("mismatch_detected", sa.Boolean(), nullable=True),
        sa.Column("policy_mismatch_detected", sa.Boolean(), nullable=True),
        sa.Column("drift_score", sa.Float(), nullable=True),
        sa.Column("replay_report_json", _json_type(), nullable=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["original_execution_id"], ["commercial_workflow_executions.id"]),
        sa.ForeignKeyConstraint(["replay_execution_id"], ["commercial_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_workflow_replay_sessions_tenant_status",
        "commercial_workflow_replay_sessions",
        ["tenant_id", "session_status"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_replay_sessions_orig",
        "commercial_workflow_replay_sessions",
        ["original_execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_replay_sessions_replay",
        "commercial_workflow_replay_sessions",
        ["replay_execution_id"],
        unique=False,
    )

    op.create_table(
        "commercial_workflow_governance_events",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("stage_id", _uuid_type(), nullable=True),
        sa.Column("replay_session_id", _uuid_type(), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("actor_metadata_json", _json_type(), nullable=True),
        sa.Column("event_summary", sa.Text(), nullable=True),
        sa.Column("event_payload_json", _json_type(), nullable=True),
        sa.Column("previous_event_hash", sa.String(length=64), nullable=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("ledger_hash", sa.String(length=64), nullable=False),
        sa.Column("detached_signature", sa.String(length=255), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_workflow_executions.id"]),
        sa.ForeignKeyConstraint(["replay_session_id"], ["commercial_workflow_replay_sessions.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["commercial_workflow_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_workflow_gov_events_exec_time",
        "commercial_workflow_governance_events",
        ["execution_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_gov_events_tenant_type",
        "commercial_workflow_governance_events",
        ["tenant_id", "event_type"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_gov_events_event_hash",
        "commercial_workflow_governance_events",
        ["event_hash"],
        unique=False,
    )
    op.create_index(
        "ix_comm_workflow_gov_events_ledger_hash",
        "commercial_workflow_governance_events",
        ["ledger_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_comm_workflow_gov_events_ledger_hash",
        table_name="commercial_workflow_governance_events",
    )
    op.drop_index(
        "ix_comm_workflow_gov_events_event_hash", table_name="commercial_workflow_governance_events"
    )
    op.drop_index(
        "ix_comm_workflow_gov_events_tenant_type",
        table_name="commercial_workflow_governance_events",
    )
    op.drop_index(
        "ix_comm_workflow_gov_events_exec_time", table_name="commercial_workflow_governance_events"
    )
    op.drop_table("commercial_workflow_governance_events")

    op.drop_index(
        "ix_comm_workflow_replay_sessions_replay", table_name="commercial_workflow_replay_sessions"
    )
    op.drop_index(
        "ix_comm_workflow_replay_sessions_orig", table_name="commercial_workflow_replay_sessions"
    )
    op.drop_index(
        "ix_comm_workflow_replay_sessions_tenant_status",
        table_name="commercial_workflow_replay_sessions",
    )
    op.drop_table("commercial_workflow_replay_sessions")

    op.drop_index(
        "ix_comm_workflow_approvals_decision_hash", table_name="commercial_workflow_approvals"
    )
    op.drop_index("ix_comm_workflow_approvals_expires", table_name="commercial_workflow_approvals")
    op.drop_index(
        "ix_comm_workflow_approvals_tenant_status", table_name="commercial_workflow_approvals"
    )
    op.drop_index("ix_comm_workflow_approvals_chain", table_name="commercial_workflow_approvals")
    op.drop_table("commercial_workflow_approvals")

    op.drop_constraint(
        "fk_workflow_stages_policy_snapshot", "commercial_workflow_stages", type_="foreignkey"
    )

    op.drop_index(
        "ix_comm_workflow_policy_snapshots_runtime_hash",
        table_name="commercial_workflow_policy_snapshots",
    )
    op.drop_index(
        "ix_comm_workflow_policy_snapshots_policy_hash",
        table_name="commercial_workflow_policy_snapshots",
    )
    op.drop_index(
        "ix_comm_workflow_policy_snapshots_tenant_hash",
        table_name="commercial_workflow_policy_snapshots",
    )
    op.drop_index(
        "ix_comm_workflow_policy_snapshots_exec_stage",
        table_name="commercial_workflow_policy_snapshots",
    )
    op.drop_table("commercial_workflow_policy_snapshots")

    op.drop_index(
        "ix_comm_workflow_policy_bindings_snapshot_hash",
        table_name="commercial_workflow_policy_bindings",
    )
    op.drop_index(
        "ix_comm_workflow_policy_bindings_runtime_hash",
        table_name="commercial_workflow_policy_bindings",
    )
    op.drop_index(
        "ix_comm_workflow_policy_bindings_tenant_status",
        table_name="commercial_workflow_policy_bindings",
    )
    op.drop_index(
        "ix_comm_workflow_policy_bindings_exec_stage",
        table_name="commercial_workflow_policy_bindings",
    )
    op.drop_table("commercial_workflow_policy_bindings")

    op.drop_constraint(
        "fk_workflow_stages_bound_policy_bundle", "commercial_workflow_stages", type_="foreignkey"
    )
    op.drop_column("commercial_workflow_stages", "drift_status")
    op.drop_column("commercial_workflow_stages", "governance_mode")
    op.drop_column("commercial_workflow_stages", "governance_decision_signature")
    op.drop_column("commercial_workflow_stages", "approval_status")
    op.drop_column("commercial_workflow_stages", "approval_required")
    op.drop_column("commercial_workflow_stages", "active_policy_snapshot_id")
    op.drop_column("commercial_workflow_stages", "bound_policy_bundle_id")

    op.drop_index(
        "ix_commercial_workflow_executions_replay_status",
        table_name="commercial_workflow_executions",
    )
    op.drop_index(
        "ix_commercial_workflow_executions_governance_status",
        table_name="commercial_workflow_executions",
    )
    op.drop_column("commercial_workflow_executions", "confidential_metadata")
    op.drop_column("commercial_workflow_executions", "replay_status")
    op.drop_column("commercial_workflow_executions", "governance_status")
    op.drop_column("commercial_workflow_executions", "governance_ledger_hash")
