"""commercial_qos_tiers

Revision ID: 20260514_0041
Revises: 20260514_0040
Create Date: 2026-05-14 16:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260514_0041"
down_revision = "20260514_0040"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_qos_tiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("target_latency_ms", sa.Integer(), nullable=False),
        sa.Column("max_p95_latency_ms", sa.Integer(), nullable=False),
        sa.Column("min_margin_percent", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("max_cost_per_request_brl", sa.Numeric(precision=14, scale=8), nullable=False),
        sa.Column("allow_cloud", sa.Boolean(), nullable=False),
        sa.Column("allow_cross_cluster", sa.Boolean(), nullable=False),
        sa.Column("allow_degraded_cluster", sa.Boolean(), nullable=False),
        sa.Column("allow_fallback_local", sa.Boolean(), nullable=False),
        sa.Column("queue_priority", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("streaming_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("quality_floor", sa.Integer(), nullable=True),
        sa.Column("degradation_policy", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_qos_tiers_name"), "commercial_qos_tiers", ["name"], unique=True
    )

    # Add fields to commercial_routing_events for SLA tracking
    op.add_column(
        "commercial_routing_events", sa.Column("qos_tier", sa.String(length=64), nullable=True)
    )
    op.add_column("commercial_routing_events", sa.Column("sla_pass", sa.Boolean(), nullable=True))
    op.add_column(
        "commercial_routing_events",
        sa.Column("degradation_applied", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_routing_events", sa.Column("qos_priority", sa.Integer(), nullable=True)
    )

    # Add priority to generation_jobs
    op.add_column(
        "generation_jobs", sa.Column("priority", sa.Integer(), server_default="100", nullable=False)
    )


def downgrade():
    op.drop_column("generation_jobs", "priority")
    op.drop_column("commercial_routing_events", "qos_priority")
    op.drop_column("commercial_routing_events", "degradation_applied")
    op.drop_column("commercial_routing_events", "sla_pass")
    op.drop_column("commercial_routing_events", "qos_tier")
    op.drop_index(op.f("ix_commercial_qos_tiers_name"), table_name="commercial_qos_tiers")
    op.drop_table("commercial_qos_tiers")
