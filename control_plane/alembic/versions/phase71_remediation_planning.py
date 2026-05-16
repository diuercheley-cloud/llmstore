"""Phase 71 Deterministic Remediation Planning

Revision ID: phase71_remediation_planning
Revises: phase70_correlation_engine
Create Date: 2026-05-15 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase71_remediation_planning"
down_revision = "phase70_correlation_engine"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. RemediationPlan
    op.create_table(
        "remediation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_type", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("blast_radius", sa.String(length=50), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("deterministic_version", sa.String(length=50), nullable=False, server_default="v1"),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_plans_client_id", "remediation_plans", ["client_id"], unique=False)
    op.create_index("ix_remediation_plans_plan_type", "remediation_plans", ["plan_type"], unique=False)
    op.create_index("ix_remediation_plans_input_hash", "remediation_plans", ["input_hash"], unique=False)
    op.create_index("ix_remediation_plans_immutable_hash", "remediation_plans", ["immutable_hash"], unique=False)
    op.create_index("ix_remediation_plans_status", "remediation_plans", ["status"], unique=False)

    # 2. RemediationStep
    op.create_table(
        "remediation_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("target_domain", sa.String(length=100), nullable=False),
        sa.Column("target_ref", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("expected_effect", sa.String(length=1000), nullable=False),
        sa.Column("reversible", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["remediation_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_steps_client_id", "remediation_steps", ["client_id"], unique=False)
    op.create_index("ix_remediation_steps_plan_id", "remediation_steps", ["plan_id"], unique=False)
    op.create_index("ix_remediation_steps_immutable_hash", "remediation_steps", ["immutable_hash"], unique=False)

    # 3. RemediationPlanReceipt
    op.create_table(
        "remediation_plan_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_type", sa.String(length=100), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["remediation_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_plan_receipts_client_id", "remediation_plan_receipts", ["client_id"], unique=False)
    op.create_index("ix_remediation_plan_receipts_plan_id", "remediation_plan_receipts", ["plan_id"], unique=False)
    op.create_index("ix_remediation_plan_receipts_immutable_hash", "remediation_plan_receipts", ["immutable_hash"], unique=False)

    # 4. RemediationApprovalRequirement
    op.create_table(
        "remediation_approval_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_scope", sa.String(length=100), nullable=False),
        sa.Column("required_role", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["remediation_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("immutable_hash")
    )
    op.create_index("ix_remediation_approval_requirements_client_id", "remediation_approval_requirements", ["client_id"], unique=False)
    op.create_index("ix_remediation_approval_requirements_plan_id", "remediation_approval_requirements", ["plan_id"], unique=False)
    op.create_index("ix_remediation_approval_requirements_immutable_hash", "remediation_approval_requirements", ["immutable_hash"], unique=False)

def downgrade() -> None:
    op.drop_table("remediation_approval_requirements")
    op.drop_table("remediation_plan_receipts")
    op.drop_table("remediation_steps")
    op.drop_table("remediation_plans")
