"""enterprise_policy_governance

Revision ID: 20260514_0052
Revises: 20260514_0051
Create Date: 2026-05-14 23:59:30.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0052"
down_revision = "20260514_0051"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_policy_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bundle_name", sa.String(length=255), nullable=False),
        sa.Column("bundle_version", sa.String(length=64), nullable=False),
        sa.Column("bundle_type", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signed_by", sa.String(length=255), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_policy_bundles_bundle_type"), "commercial_policy_bundles", ["bundle_type"], unique=False)
    op.create_index(op.f("ix_commercial_policy_bundles_client_id"), "commercial_policy_bundles", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_policy_bundles_immutable_hash"), "commercial_policy_bundles", ["immutable_hash"], unique=False)
    op.create_index(op.f("ix_commercial_policy_bundles_status"), "commercial_policy_bundles", ["status"], unique=False)

    op.create_table(
        "commercial_policy_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("artifact_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["commercial_policy_bundles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_policy_artifacts_artifact_hash"), "commercial_policy_artifacts", ["artifact_hash"], unique=False)
    op.create_index(op.f("ix_commercial_policy_artifacts_artifact_type"), "commercial_policy_artifacts", ["artifact_type"], unique=False)
    op.create_index(op.f("ix_commercial_policy_artifacts_bundle_id"), "commercial_policy_artifacts", ["bundle_id"], unique=False)

    op.create_table(
        "commercial_policy_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_chain_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approval_chain_id"], ["commercial_approval_chains.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bundle_id"], ["commercial_policy_bundles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_policy_approvals_approval_chain_id"), "commercial_policy_approvals", ["approval_chain_id"], unique=False)
    op.create_index(op.f("ix_commercial_policy_approvals_bundle_id"), "commercial_policy_approvals", ["bundle_id"], unique=False)
    op.create_index(op.f("ix_commercial_policy_approvals_status"), "commercial_policy_approvals", ["status"], unique=False)

    op.create_table(
        "commercial_policy_drift_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("expected_hash", sa.String(length=64), nullable=True),
        sa.Column("observed_hash", sa.String(length=64), nullable=True),
        sa.Column("drift_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["bundle_id"], ["commercial_policy_bundles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_policy_drift_events_bundle_id"), "commercial_policy_drift_events", ["bundle_id"], unique=False)
    op.create_index(op.f("ix_commercial_policy_drift_events_drift_type"), "commercial_policy_drift_events", ["drift_type"], unique=False)
    op.create_index(op.f("ix_commercial_policy_drift_events_resolved"), "commercial_policy_drift_events", ["resolved"], unique=False)
    op.create_index(op.f("ix_commercial_policy_drift_events_severity"), "commercial_policy_drift_events", ["severity"], unique=False)


def downgrade():
    op.drop_table("commercial_policy_drift_events")
    op.drop_table("commercial_policy_approvals")
    op.drop_table("commercial_policy_artifacts")
    op.drop_table("commercial_policy_bundles")
