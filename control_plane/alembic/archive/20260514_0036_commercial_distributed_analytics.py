"""commercial distributed analytics

Revision ID: 20260514_0036
Revises: 20260514_0035, aa5096efa31a
Create Date: 2026-05-14 15:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0036"
down_revision = ("20260514_0035", "aa5096efa31a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_node_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("node_role", sa.String(length=32), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("app_version", sa.String(length=64), nullable=True),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_node_heartbeats_node_id",
        "commercial_node_heartbeats",
        ["node_id"],
        unique=True,
    )
    op.create_index(
        "ix_commercial_node_heartbeats_node_role",
        "commercial_node_heartbeats",
        ["node_role"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_node_heartbeats_last_seen_at",
        "commercial_node_heartbeats",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_node_heartbeats_status",
        "commercial_node_heartbeats",
        ["status"],
        unique=False,
    )

    op.create_table(
        "commercial_routing_event_ingest",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_event_id",
        "commercial_routing_event_ingest",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_correlation_id",
        "commercial_routing_event_ingest",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_request_id",
        "commercial_routing_event_ingest",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_node_id",
        "commercial_routing_event_ingest",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_received_at",
        "commercial_routing_event_ingest",
        ["received_at"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_processed_at",
        "commercial_routing_event_ingest",
        ["processed_at"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_status",
        "commercial_routing_event_ingest",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_routing_event_ingest_dedupe_key",
        "commercial_routing_event_ingest",
        ["dedupe_key"],
        unique=False,
    )

    op.create_table(
        "commercial_cluster_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_minutes", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("requests_count", sa.Integer(), nullable=False),
        sa.Column("fallback_count", sa.Integer(), nullable=False),
        sa.Column("block_count", sa.Integer(), nullable=False),
        sa.Column("estimated_revenue_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("estimated_cost_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("actual_revenue_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("actual_cost_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("actual_margin_brl", sa.Numeric(precision=14, scale=8), nullable=True),
        sa.Column("avg_latency_ms", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_bucket_start",
        "commercial_cluster_aggregates",
        ["bucket_start"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_bucket_minutes",
        "commercial_cluster_aggregates",
        ["bucket_minutes"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_node_id",
        "commercial_cluster_aggregates",
        ["node_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_provider",
        "commercial_cluster_aggregates",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_model",
        "commercial_cluster_aggregates",
        ["model"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_client_id",
        "commercial_cluster_aggregates",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_created_at",
        "commercial_cluster_aggregates",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_cluster_aggregates_bucket_scope",
        "commercial_cluster_aggregates",
        ["bucket_start", "bucket_minutes", "node_id", "provider", "model", "client_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_commercial_cluster_aggregates_bucket_scope", table_name="commercial_cluster_aggregates"
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_created_at", table_name="commercial_cluster_aggregates"
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_client_id", table_name="commercial_cluster_aggregates"
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_model", table_name="commercial_cluster_aggregates"
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_provider", table_name="commercial_cluster_aggregates"
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_node_id", table_name="commercial_cluster_aggregates"
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_bucket_minutes",
        table_name="commercial_cluster_aggregates",
    )
    op.drop_index(
        "ix_commercial_cluster_aggregates_bucket_start", table_name="commercial_cluster_aggregates"
    )
    op.drop_table("commercial_cluster_aggregates")

    op.drop_index(
        "ix_commercial_routing_event_ingest_dedupe_key",
        table_name="commercial_routing_event_ingest",
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_status", table_name="commercial_routing_event_ingest"
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_processed_at",
        table_name="commercial_routing_event_ingest",
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_received_at",
        table_name="commercial_routing_event_ingest",
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_node_id", table_name="commercial_routing_event_ingest"
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_request_id",
        table_name="commercial_routing_event_ingest",
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_correlation_id",
        table_name="commercial_routing_event_ingest",
    )
    op.drop_index(
        "ix_commercial_routing_event_ingest_event_id", table_name="commercial_routing_event_ingest"
    )
    op.drop_table("commercial_routing_event_ingest")

    op.drop_index("ix_commercial_node_heartbeats_status", table_name="commercial_node_heartbeats")
    op.drop_index(
        "ix_commercial_node_heartbeats_last_seen_at", table_name="commercial_node_heartbeats"
    )
    op.drop_index(
        "ix_commercial_node_heartbeats_node_role", table_name="commercial_node_heartbeats"
    )
    op.drop_index("ix_commercial_node_heartbeats_node_id", table_name="commercial_node_heartbeats")
    op.drop_table("commercial_node_heartbeats")
