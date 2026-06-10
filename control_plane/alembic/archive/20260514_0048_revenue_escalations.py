"""revenue_escalations

Revision ID: 20260514_0048
Revises: 20260514_0047
Create Date: 2026-05-14 23:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0048"
down_revision = "20260514_0047"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_revenue_alert_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("delivery_type", sa.String(length=16), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_created_at"), "commercial_revenue_alert_deliveries", ["created_at"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_delivery_type"), "commercial_revenue_alert_deliveries", ["delivery_type"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_dedupe_key"), "commercial_revenue_alert_deliveries", ["dedupe_key"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_payload_hash"), "commercial_revenue_alert_deliveries", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_severity"), "commercial_revenue_alert_deliveries", ["severity"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_source_id"), "commercial_revenue_alert_deliveries", ["source_id"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_source_type"), "commercial_revenue_alert_deliveries", ["source_type"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_alert_deliveries_status"), "commercial_revenue_alert_deliveries", ["status"], unique=False)
    op.create_index(
        "ix_commercial_revenue_alert_deliveries_dedupe_delivery_type",
        "commercial_revenue_alert_deliveries",
        ["dedupe_key", "delivery_type"],
        unique=False,
    )

    op.create_table(
        "commercial_revenue_escalation_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("severity_threshold", sa.String(length=16), nullable=False),
        sa.Column("trigger_types_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("allowed_delivery_types_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("escalation_order_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_revenue_escalation_policies_enabled"), "commercial_revenue_escalation_policies", ["enabled"], unique=False)
    op.create_index(op.f("ix_commercial_revenue_escalation_policies_severity_threshold"), "commercial_revenue_escalation_policies", ["severity_threshold"], unique=False)


def downgrade():
    op.drop_table("commercial_revenue_escalation_policies")
    op.drop_index("ix_commercial_revenue_alert_deliveries_dedupe_delivery_type", table_name="commercial_revenue_alert_deliveries")
    op.drop_table("commercial_revenue_alert_deliveries")
