"""Phase 72 Approval-Gated Remediation Execution

Revision ID: phase72_remediation_execution
Revises: phase71_remediation_planning
Create Date: 2026-05-15 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase72_remediation_execution"
down_revision = "phase71_remediation_planning"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. RemediationExecution
    op.create_table(
        "remediation_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_mode", sa.String(length=50), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("approval_verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("kill_switch_checked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("blast_radius_checked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("rollback_plan_present", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("deterministic_version", sa.String(length=50), nullable=False, server_default="v1"),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["remediation_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_executions_client_id", "remediation_executions", ["client_id"], unique=False)
    op.create_index("ix_remediation_executions_plan_id", "remediation_executions", ["plan_id"], unique=False)
    op.create_index("ix_remediation_executions_status", "remediation_executions", ["status"], unique=False)
    op.create_index("ix_remediation_executions_immutable_hash", "remediation_executions", ["immutable_hash"], unique=False)

    # 2. RemediationExecutionStep
    op.create_table(
        "remediation_execution_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_domain", sa.String(length=100), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column("execution_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("simulated_result_json", sa.JSON(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["remediation_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_step_id"], ["remediation_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_execution_steps_client_id", "remediation_execution_steps", ["client_id"], unique=False)
    op.create_index("ix_remediation_execution_steps_execution_id", "remediation_execution_steps", ["execution_id"], unique=False)
    op.create_index("ix_remediation_execution_steps_immutable_hash", "remediation_execution_steps", ["immutable_hash"], unique=False)

    # 3. RemediationRollbackPlan
    op.create_table(
        "remediation_rollback_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rollback_strategy", sa.String(length=100), nullable=False),
        sa.Column("rollback_steps_json", sa.JSON(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["remediation_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["remediation_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_rollback_plans_client_id", "remediation_rollback_plans", ["client_id"], unique=False)
    op.create_index("ix_remediation_rollback_plans_plan_id", "remediation_rollback_plans", ["plan_id"], unique=False)
    op.create_index("ix_remediation_rollback_plans_execution_id", "remediation_rollback_plans", ["execution_id"], unique=False)
    op.create_index("ix_remediation_rollback_plans_immutable_hash", "remediation_rollback_plans", ["immutable_hash"], unique=False)

    # 4. RemediationExecutionReceipt
    op.create_table(
        "remediation_execution_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_type", sa.String(length=100), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["remediation_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_execution_receipts_client_id", "remediation_execution_receipts", ["client_id"], unique=False)
    op.create_index("ix_remediation_execution_receipts_execution_id", "remediation_execution_receipts", ["execution_id"], unique=False)
    op.create_index("ix_remediation_execution_receipts_immutable_hash", "remediation_execution_receipts", ["immutable_hash"], unique=False)

    # 5. RemediationKillSwitchState
    op.create_table(
        "remediation_kill_switch_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_kill_switch_states_client_id", "remediation_kill_switch_states", ["client_id"], unique=False)
    op.create_index("ix_remediation_kill_switch_states_immutable_hash", "remediation_kill_switch_states", ["immutable_hash"], unique=False)

def downgrade() -> None:
    op.drop_table("remediation_kill_switch_states")
    op.drop_table("remediation_execution_receipts")
    op.drop_table("remediation_rollback_plans")
    op.drop_table("remediation_execution_steps")
    op.drop_table("remediation_executions")
