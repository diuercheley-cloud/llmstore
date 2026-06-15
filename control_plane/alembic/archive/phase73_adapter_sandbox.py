"""Phase 73 Controlled Adapter Sandbox

Revision ID: phase73_adapter_sandbox
Revises: phase72_remediation_execution
Create Date: 2026-05-15 22:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "phase73_adapter_sandbox"
down_revision = "phase72_remediation_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. AdapterManifest
    op.create_table(
        "adapter_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("adapter_name", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("adapter_type", sa.String(length=50), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("denied_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("sandbox_required", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("dry_run_default", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("network_access_allowed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("subprocess_allowed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "external_system_access_allowed", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "deterministic_version", sa.String(length=50), nullable=False, server_default="v1"
        ),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash"),
    )
    op.create_index(
        "ix_adapter_manifests_client_id", "adapter_manifests", ["client_id"], unique=False
    )
    op.create_index(
        "ix_adapter_manifests_adapter_name", "adapter_manifests", ["adapter_name"], unique=False
    )
    op.create_index(
        "ix_adapter_manifests_manifest_hash", "adapter_manifests", ["manifest_hash"], unique=False
    )
    op.create_index(
        "ix_adapter_manifests_immutable_hash", "adapter_manifests", ["immutable_hash"], unique=False
    )

    # 2. AdapterSandboxRun
    op.create_table(
        "adapter_sandbox_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manifest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sandbox_mode", sa.String(length=50), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("approval_verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("gates_verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manifest_id"], ["adapter_manifests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["remediation_executions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["remediation_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash"),
    )
    op.create_index(
        "ix_adapter_sandbox_runs_client_id", "adapter_sandbox_runs", ["client_id"], unique=False
    )
    op.create_index(
        "ix_adapter_sandbox_runs_manifest_id", "adapter_sandbox_runs", ["manifest_id"], unique=False
    )
    op.create_index(
        "ix_adapter_sandbox_runs_status", "adapter_sandbox_runs", ["status"], unique=False
    )
    op.create_index(
        "ix_adapter_sandbox_runs_immutable_hash",
        "adapter_sandbox_runs",
        ["immutable_hash"],
        unique=False,
    )

    # 3. AdapterSandboxStepResult
    op.create_table(
        "adapter_sandbox_step_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sandbox_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_domain", sa.String(length=100), nullable=False),
        sa.Column("result_status", sa.String(length=50), nullable=False),
        sa.Column("simulated_output_json", sa.JSON(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sandbox_run_id"], ["adapter_sandbox_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash"),
    )
    op.create_index(
        "ix_adapter_sandbox_step_results_client_id",
        "adapter_sandbox_step_results",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_adapter_sandbox_step_results_sandbox_run_id",
        "adapter_sandbox_step_results",
        ["sandbox_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_adapter_sandbox_step_results_immutable_hash",
        "adapter_sandbox_step_results",
        ["immutable_hash"],
        unique=False,
    )

    # 4. AdapterSandboxPolicyViolation
    op.create_table(
        "adapter_sandbox_policy_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("manifest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sandbox_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("violation_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manifest_id"], ["adapter_manifests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sandbox_run_id"], ["adapter_sandbox_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash"),
    )
    op.create_index(
        "ix_adapter_sandbox_policy_violations_client_id",
        "adapter_sandbox_policy_violations",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_adapter_sandbox_policy_violations_violation_type",
        "adapter_sandbox_policy_violations",
        ["violation_type"],
        unique=False,
    )
    op.create_index(
        "ix_adapter_sandbox_policy_violations_immutable_hash",
        "adapter_sandbox_policy_violations",
        ["immutable_hash"],
        unique=False,
    )

    # 5. AdapterSandboxReceipt
    op.create_table(
        "adapter_sandbox_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sandbox_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receipt_type", sa.String(length=100), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sandbox_run_id"], ["adapter_sandbox_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash"),
    )
    op.create_index(
        "ix_adapter_sandbox_receipts_client_id",
        "adapter_sandbox_receipts",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_adapter_sandbox_receipts_sandbox_run_id",
        "adapter_sandbox_receipts",
        ["sandbox_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_adapter_sandbox_receipts_immutable_hash",
        "adapter_sandbox_receipts",
        ["immutable_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("adapter_sandbox_receipts")
    op.drop_table("adapter_sandbox_policy_violations")
    op.drop_table("adapter_sandbox_step_results")
    op.drop_table("adapter_sandbox_runs")
    op.drop_table("adapter_manifests")
