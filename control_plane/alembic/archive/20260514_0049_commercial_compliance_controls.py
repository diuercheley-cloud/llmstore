"""commercial_compliance_controls

Revision ID: 20260514_0049
Revises: 20260514_0048
Create Date: 2026-05-14 23:55:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0049"
down_revision = "20260514_0048"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_control_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("control_area", sa.String(length=48), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("required_approver_count", sa.Integer(), nullable=False),
        sa.Column("segregation_required", sa.Boolean(), nullable=False),
        sa.Column("evidence_required", sa.Boolean(), nullable=False),
        sa.Column("review_frequency", sa.String(length=16), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_control_policies_action_type"), "commercial_control_policies", ["action_type"], unique=False)
    op.create_index(op.f("ix_commercial_control_policies_control_area"), "commercial_control_policies", ["control_area"], unique=False)
    op.create_index(op.f("ix_commercial_control_policies_enabled"), "commercial_control_policies", ["enabled"], unique=False)

    op.create_table(
        "commercial_evidence_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_type", sa.String(length=48), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("file_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_evidence_packages_created_at"), "commercial_evidence_packages", ["created_at"], unique=False)
    op.create_index(op.f("ix_commercial_evidence_packages_immutable_hash"), "commercial_evidence_packages", ["immutable_hash"], unique=False)
    op.create_index(op.f("ix_commercial_evidence_packages_package_type"), "commercial_evidence_packages", ["package_type"], unique=False)
    op.create_index(op.f("ix_commercial_evidence_packages_target_id"), "commercial_evidence_packages", ["target_id"], unique=False)
    op.create_index(op.f("ix_commercial_evidence_packages_target_type"), "commercial_evidence_packages", ["target_type"], unique=False)

    op.create_table(
        "commercial_approval_chains",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("required_approver_count", sa.Integer(), nullable=False),
        sa.Column("approvals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rejections_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["control_policy_id"], ["commercial_control_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_package_id"], ["commercial_evidence_packages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_approval_chains_control_policy_id"), "commercial_approval_chains", ["control_policy_id"], unique=False)
    op.create_index(op.f("ix_commercial_approval_chains_evidence_package_id"), "commercial_approval_chains", ["evidence_package_id"], unique=False)
    op.create_index(op.f("ix_commercial_approval_chains_requested_by"), "commercial_approval_chains", ["requested_by"], unique=False)
    op.create_index(op.f("ix_commercial_approval_chains_status"), "commercial_approval_chains", ["status"], unique=False)
    op.create_index(op.f("ix_commercial_approval_chains_target_id"), "commercial_approval_chains", ["target_id"], unique=False)
    op.create_index(op.f("ix_commercial_approval_chains_target_type"), "commercial_approval_chains", ["target_type"], unique=False)

    op.create_table(
        "commercial_control_attestations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attestation_period_start", sa.Date(), nullable=False),
        sa.Column("attestation_period_end", sa.Date(), nullable=False),
        sa.Column("attested_by", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evidence_package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["control_policy_id"], ["commercial_control_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_package_id"], ["commercial_evidence_packages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_control_attestations_attestation_period_end"), "commercial_control_attestations", ["attestation_period_end"], unique=False)
    op.create_index(op.f("ix_commercial_control_attestations_attestation_period_start"), "commercial_control_attestations", ["attestation_period_start"], unique=False)
    op.create_index(op.f("ix_commercial_control_attestations_control_policy_id"), "commercial_control_attestations", ["control_policy_id"], unique=False)
    op.create_index(op.f("ix_commercial_control_attestations_evidence_package_id"), "commercial_control_attestations", ["evidence_package_id"], unique=False)
    op.create_index(op.f("ix_commercial_control_attestations_status"), "commercial_control_attestations", ["status"], unique=False)

    op.create_table(
        "commercial_control_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exception_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("remediation_plan", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["control_policy_id"], ["commercial_control_policies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_control_exceptions_control_policy_id"), "commercial_control_exceptions", ["control_policy_id"], unique=False)
    op.create_index(op.f("ix_commercial_control_exceptions_exception_type"), "commercial_control_exceptions", ["exception_type"], unique=False)
    op.create_index(op.f("ix_commercial_control_exceptions_severity"), "commercial_control_exceptions", ["severity"], unique=False)
    op.create_index(op.f("ix_commercial_control_exceptions_status"), "commercial_control_exceptions", ["status"], unique=False)


def downgrade():
    op.drop_table("commercial_control_exceptions")
    op.drop_table("commercial_control_attestations")
    op.drop_table("commercial_approval_chains")
    op.drop_table("commercial_evidence_packages")
    op.drop_table("commercial_control_policies")
