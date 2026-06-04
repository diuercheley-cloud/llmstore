"""revenue_protection_policy

Revision ID: 20260514_0047
Revises: 20260514_0046
Create Date: 2026-05-14 23:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0047"
down_revision = "20260514_0046"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_revenue_protection_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("severity_threshold", sa.String(length=16), nullable=False),
        sa.Column("action_type", sa.String(length=48), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_identifier", sa.String(length=255), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_revenue_protection_policies_enabled"), "commercial_revenue_protection_policies", ["enabled"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_policies_scope_identifier"), "commercial_revenue_protection_policies", ["scope_identifier"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_policies_scope_type"), "commercial_revenue_protection_policies", ["scope_type"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_policies_trigger_type"), "commercial_revenue_protection_policies", ["trigger_type"], unique=False)

    op.create_table(
        "commercial_revenue_protection_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anomaly_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("action_type", sa.String(length=48), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("approval_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["anomaly_id"], ["commercial_financial_anomalies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["commercial_revenue_protection_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_revenue_protection_actions_action_type"), "commercial_revenue_protection_actions", ["action_type"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_anomaly_id"), "commercial_revenue_protection_actions", ["anomaly_id"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_client_id"), "commercial_revenue_protection_actions", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_created_at"), "commercial_revenue_protection_actions", ["created_at"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_model"), "commercial_revenue_protection_actions", ["model"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_policy_id"), "commercial_revenue_protection_actions", ["policy_id"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_provider"), "commercial_revenue_protection_actions", ["provider"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_protection_actions_status"), "commercial_revenue_protection_actions", ["status"], unique=False)


def downgrade():
    op.drop_table("commercial_revenue_protection_actions")
    op.drop_table("commercial_revenue_protection_policies")
