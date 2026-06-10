"""phase54_agentic_execution

Revision ID: 20260515_phase54
Revises: d91c7b2e3f4a, 3b1a2c4d5e6f
Create Date: 2026-05-15 16:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_phase54"
down_revision = ("d91c7b2e3f4a", "3b1a2c4d5e6f")
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("commercial_agent_profiles", sa.Column("allowed_tenants_json", sa.JSON(), nullable=True))
    op.add_column("commercial_agent_profiles", sa.Column("agent_permissions_json", sa.JSON(), nullable=True))
    op.add_column("commercial_agent_profiles", sa.Column("max_actions_per_minute", sa.Integer(), nullable=True))
    op.add_column("commercial_agent_profiles", sa.Column("max_actions_per_day", sa.Integer(), nullable=True))

    op.add_column("commercial_agent_executions", sa.Column("tenant_id", sa.String(length=64), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("plan_hash", sa.String(length=128), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("execution_graph_hash", sa.String(length=128), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("runtime_snapshot_hash", sa.String(length=128), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("audit_chain_hash", sa.String(length=128), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("policy_decision", sa.String(length=32), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("replay_status", sa.String(length=32), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("runtime_mode", sa.String(length=32), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("dry_run", sa.Boolean(), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("approval_required", sa.Boolean(), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("approval_status", sa.String(length=32), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("confidential_payload_mode", sa.String(length=32), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("quota_key", sa.String(length=128), nullable=True))
    op.add_column("commercial_agent_executions", sa.Column("metadata_json", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_commercial_agent_executions_tenant_id"), "commercial_agent_executions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_agent_id"), "commercial_agent_executions", ["agent_id"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_status"), "commercial_agent_executions", ["status"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_plan_hash"), "commercial_agent_executions", ["plan_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_execution_graph_hash"), "commercial_agent_executions", ["execution_graph_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_runtime_snapshot_hash"), "commercial_agent_executions", ["runtime_snapshot_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_audit_chain_hash"), "commercial_agent_executions", ["audit_chain_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_policy_decision"), "commercial_agent_executions", ["policy_decision"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_replay_status"), "commercial_agent_executions", ["replay_status"], unique=False)
    op.create_index(op.f("ix_commercial_agent_executions_approval_status"), "commercial_agent_executions", ["approval_status"], unique=False)

    op.create_table(
        "commercial_agent_actions",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("action_index", sa.Integer(), nullable=False),
        sa.Column("action_name", sa.String(length=128), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("planned_input_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_envelope_hash", sa.String(length=128), nullable=True),
        sa.Column("result_hash", sa.String(length=128), nullable=True),
        sa.Column("action_hash", sa.String(length=128), nullable=True),
        sa.Column("previous_action_hash", sa.String(length=128), nullable=True),
        sa.Column("graph_node_hash", sa.String(length=128), nullable=True),
        sa.Column("receipt_hash", sa.String(length=128), nullable=True),
        sa.Column("detached_signature", sa.Text(), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
        sa.Column("policy_decision_json", sa.JSON(), nullable=True),
        sa.Column("sandbox_context_json", sa.JSON(), nullable=True),
        sa.Column("confidential_mode", sa.String(length=32), nullable=True),
        sa.Column("approval_status", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_agent_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_agent_actions_execution_id"), "commercial_agent_actions", ["execution_id"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_tenant_id"), "commercial_agent_actions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_tool_name"), "commercial_agent_actions", ["tool_name"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_status"), "commercial_agent_actions", ["status"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_action_hash"), "commercial_agent_actions", ["action_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_previous_action_hash"), "commercial_agent_actions", ["previous_action_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_graph_node_hash"), "commercial_agent_actions", ["graph_node_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_receipt_hash"), "commercial_agent_actions", ["receipt_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_actions_approval_status"), "commercial_agent_actions", ["approval_status"], unique=False)

    op.create_table(
        "commercial_tool_registry",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("trust_status", sa.String(length=32), nullable=True),
        sa.Column("provenance_hash", sa.String(length=128), nullable=True),
        sa.Column("provenance_signature", sa.Text(), nullable=True),
        sa.Column("signer_identity", sa.String(length=255), nullable=True),
        sa.Column("execution_mode", sa.String(length=32), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=True),
        sa.Column("allow_dry_run", sa.Boolean(), nullable=True),
        sa.Column("confidential_payload_mode", sa.String(length=32), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("quota_limit_per_day", sa.Integer(), nullable=True),
        sa.Column("policy_scope_json", sa.JSON(), nullable=True),
        sa.Column("schema_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_tool_registry_tool_name"), "commercial_tool_registry", ["tool_name"], unique=False)
    op.create_index(op.f("ix_commercial_tool_registry_tenant_id"), "commercial_tool_registry", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_commercial_tool_registry_trust_status"), "commercial_tool_registry", ["trust_status"], unique=False)

    op.create_table(
        "commercial_tool_approvals",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("action_id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("approval_chain_hash", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["action_id"], ["commercial_agent_actions.id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_agent_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_tool_approvals_action_id"), "commercial_tool_approvals", ["action_id"], unique=False)
    op.create_index(op.f("ix_commercial_tool_approvals_execution_id"), "commercial_tool_approvals", ["execution_id"], unique=False)
    op.create_index(op.f("ix_commercial_tool_approvals_tenant_id"), "commercial_tool_approvals", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_commercial_tool_approvals_status"), "commercial_tool_approvals", ["status"], unique=False)
    op.create_index(op.f("ix_commercial_tool_approvals_approval_chain_hash"), "commercial_tool_approvals", ["approval_chain_hash"], unique=False)

    op.create_table(
        "commercial_agent_replay_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("execution_id", _uuid_type(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("replay_hash", sa.String(length=128), nullable=False),
        sa.Column("original_plan_hash", sa.String(length=128), nullable=True),
        sa.Column("original_graph_hash", sa.String(length=128), nullable=True),
        sa.Column("runtime_snapshot_hash", sa.String(length=128), nullable=True),
        sa.Column("replay_graph_hash", sa.String(length=128), nullable=True),
        sa.Column("verification_result", sa.String(length=32), nullable=True),
        sa.Column("mismatch_reason", sa.Text(), nullable=True),
        sa.Column("verified_by", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_agent_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_agent_replay_records_execution_id"), "commercial_agent_replay_records", ["execution_id"], unique=False)
    op.create_index(op.f("ix_commercial_agent_replay_records_tenant_id"), "commercial_agent_replay_records", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_commercial_agent_replay_records_replay_hash"), "commercial_agent_replay_records", ["replay_hash"], unique=False)
    op.create_index(op.f("ix_commercial_agent_replay_records_verification_result"), "commercial_agent_replay_records", ["verification_result"], unique=False)


def downgrade() -> None:
    op.drop_table("commercial_agent_replay_records")
    op.drop_table("commercial_tool_approvals")
    op.drop_table("commercial_tool_registry")
    op.drop_table("commercial_agent_actions")

    op.drop_index(op.f("ix_commercial_agent_executions_approval_status"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_replay_status"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_policy_decision"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_audit_chain_hash"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_runtime_snapshot_hash"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_execution_graph_hash"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_plan_hash"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_status"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_agent_id"), table_name="commercial_agent_executions")
    op.drop_index(op.f("ix_commercial_agent_executions_tenant_id"), table_name="commercial_agent_executions")

    op.drop_column("commercial_agent_executions", "metadata_json")
    op.drop_column("commercial_agent_executions", "quota_key")
    op.drop_column("commercial_agent_executions", "confidential_payload_mode")
    op.drop_column("commercial_agent_executions", "approval_status")
    op.drop_column("commercial_agent_executions", "approval_required")
    op.drop_column("commercial_agent_executions", "dry_run")
    op.drop_column("commercial_agent_executions", "runtime_mode")
    op.drop_column("commercial_agent_executions", "replay_status")
    op.drop_column("commercial_agent_executions", "policy_decision")
    op.drop_column("commercial_agent_executions", "audit_chain_hash")
    op.drop_column("commercial_agent_executions", "runtime_snapshot_hash")
    op.drop_column("commercial_agent_executions", "execution_graph_hash")
    op.drop_column("commercial_agent_executions", "plan_hash")
    op.drop_column("commercial_agent_executions", "tenant_id")

    op.drop_column("commercial_agent_profiles", "max_actions_per_day")
    op.drop_column("commercial_agent_profiles", "max_actions_per_minute")
    op.drop_column("commercial_agent_profiles", "agent_permissions_json")
    op.drop_column("commercial_agent_profiles", "allowed_tenants_json")
