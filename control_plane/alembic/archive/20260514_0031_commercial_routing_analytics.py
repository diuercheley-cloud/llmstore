"""add commercial routing analytics events

Revision ID: 20260514_0031
Revises: 20260514_0030
Create Date: 2026-05-14 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0031"
down_revision = "20260514_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_routing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("endpoint", sa.String(length=128), nullable=True),
        sa.Column("model_requested", sa.String(length=255), nullable=True),
        sa.Column("task_type", sa.String(length=32), nullable=True),
        sa.Column("policy", sa.String(length=64), nullable=True),
        sa.Column("selected_provider", sa.String(length=64), nullable=True),
        sa.Column("selected_model", sa.String(length=255), nullable=True),
        sa.Column("selected_is_cloud", sa.Boolean(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("block_reason", sa.String(length=255), nullable=True),
        sa.Column("estimated_cost_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("estimated_revenue_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("estimated_margin_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("estimated_margin_percent", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("actual_cost_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("actual_revenue_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("actual_margin_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("actual_margin_percent", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("selected_score", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("ranked_routes_json", sa.JSON(), nullable=True),
        sa.Column("rejected_routes_json", sa.JSON(), nullable=True),
        sa.Column("guardrail_decisions_json", sa.JSON(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider_latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_routing_events_client_id", "commercial_routing_events", ["client_id"]
    )
    op.create_index(
        "ix_commercial_routing_events_created_at", "commercial_routing_events", ["created_at"]
    )
    op.create_index(
        "ix_commercial_routing_events_request_id", "commercial_routing_events", ["request_id"]
    )
    op.create_index(
        "ix_commercial_routing_events_correlation_id",
        "commercial_routing_events",
        ["correlation_id"],
    )
    op.create_index(
        "ix_commercial_routing_events_selected_provider",
        "commercial_routing_events",
        ["selected_provider"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_commercial_routing_events_selected_provider", table_name="commercial_routing_events"
    )
    op.drop_index(
        "ix_commercial_routing_events_correlation_id", table_name="commercial_routing_events"
    )
    op.drop_index("ix_commercial_routing_events_request_id", table_name="commercial_routing_events")
    op.drop_index("ix_commercial_routing_events_created_at", table_name="commercial_routing_events")
    op.drop_index("ix_commercial_routing_events_client_id", table_name="commercial_routing_events")
    op.drop_table("commercial_routing_events")
