"""add commercial federation registry and aggregates

Revision ID: 20260514_0031a
Revises: 20260514_0030
Create Date: 2026-05-14 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0031a"
down_revision = "20260514_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_cluster_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("tenant_scope_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_id", name="uq_commercial_cluster_registry_cluster_id"),
    )
    op.create_index(
        "ix_commercial_cluster_registry_cluster_id", "commercial_cluster_registry", ["cluster_id"]
    )
    op.create_index(
        "ix_commercial_cluster_registry_region", "commercial_cluster_registry", ["region"]
    )
    op.create_index(
        "ix_commercial_cluster_registry_environment", "commercial_cluster_registry", ["environment"]
    )
    op.create_index(
        "ix_commercial_cluster_registry_status", "commercial_cluster_registry", ["status"]
    )
    op.create_index(
        "ix_commercial_cluster_registry_priority", "commercial_cluster_registry", ["priority"]
    )
    op.create_index(
        "ix_commercial_cluster_registry_last_seen_at",
        "commercial_cluster_registry",
        ["last_seen_at"],
    )
    op.create_index(
        "ix_commercial_cluster_registry_created_at", "commercial_cluster_registry", ["created_at"]
    )
    op.create_index(
        "ix_commercial_cluster_registry_updated_at", "commercial_cluster_registry", ["updated_at"]
    )

    op.create_table(
        "commercial_federated_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_cluster_id", sa.String(length=128), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_minutes", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("requests_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("block_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_revenue_brl", sa.Numeric(14, 8), nullable=True),
        sa.Column("estimated_cost_brl", sa.Numeric(14, 8), nullable=True),
        sa.Column("actual_revenue_brl", sa.Numeric(14, 8), nullable=True),
        sa.Column("actual_cost_brl", sa.Numeric(14, 8), nullable=True),
        sa.Column("actual_margin_brl", sa.Numeric(14, 8), nullable=True),
        sa.Column("avg_latency_ms", sa.Numeric(14, 4), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_commercial_federated_aggregates_dedupe_key"),
    )
    op.create_index(
        "ix_commercial_federated_aggregates_source_cluster_id",
        "commercial_federated_aggregates",
        ["source_cluster_id"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_bucket_start",
        "commercial_federated_aggregates",
        ["bucket_start"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_bucket_minutes",
        "commercial_federated_aggregates",
        ["bucket_minutes"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_provider",
        "commercial_federated_aggregates",
        ["provider"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_model", "commercial_federated_aggregates", ["model"]
    )
    op.create_index(
        "ix_commercial_federated_aggregates_client_id",
        "commercial_federated_aggregates",
        ["client_id"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_tenant_id",
        "commercial_federated_aggregates",
        ["tenant_id"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_received_at",
        "commercial_federated_aggregates",
        ["received_at"],
    )
    op.create_index(
        "ix_commercial_federated_aggregates_dedupe_key",
        "commercial_federated_aggregates",
        ["dedupe_key"],
    )

    op.create_table(
        "commercial_cluster_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_cluster_id", sa.String(length=128), nullable=False),
        sa.Column("sync_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_duplicate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_cluster_sync_logs_source_cluster_id",
        "commercial_cluster_sync_logs",
        ["source_cluster_id"],
    )
    op.create_index(
        "ix_commercial_cluster_sync_logs_sync_type", "commercial_cluster_sync_logs", ["sync_type"]
    )
    op.create_index(
        "ix_commercial_cluster_sync_logs_status", "commercial_cluster_sync_logs", ["status"]
    )
    op.create_index(
        "ix_commercial_cluster_sync_logs_started_at", "commercial_cluster_sync_logs", ["started_at"]
    )
    op.create_index(
        "ix_commercial_cluster_sync_logs_finished_at",
        "commercial_cluster_sync_logs",
        ["finished_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_commercial_cluster_sync_logs_finished_at", table_name="commercial_cluster_sync_logs"
    )
    op.drop_index(
        "ix_commercial_cluster_sync_logs_started_at", table_name="commercial_cluster_sync_logs"
    )
    op.drop_index(
        "ix_commercial_cluster_sync_logs_status", table_name="commercial_cluster_sync_logs"
    )
    op.drop_index(
        "ix_commercial_cluster_sync_logs_sync_type", table_name="commercial_cluster_sync_logs"
    )
    op.drop_index(
        "ix_commercial_cluster_sync_logs_source_cluster_id",
        table_name="commercial_cluster_sync_logs",
    )
    op.drop_table("commercial_cluster_sync_logs")

    op.drop_index(
        "ix_commercial_federated_aggregates_dedupe_key",
        table_name="commercial_federated_aggregates",
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_received_at",
        table_name="commercial_federated_aggregates",
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_tenant_id", table_name="commercial_federated_aggregates"
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_client_id", table_name="commercial_federated_aggregates"
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_model", table_name="commercial_federated_aggregates"
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_provider", table_name="commercial_federated_aggregates"
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_bucket_minutes",
        table_name="commercial_federated_aggregates",
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_bucket_start",
        table_name="commercial_federated_aggregates",
    )
    op.drop_index(
        "ix_commercial_federated_aggregates_source_cluster_id",
        table_name="commercial_federated_aggregates",
    )
    op.drop_table("commercial_federated_aggregates")

    op.drop_index(
        "ix_commercial_cluster_registry_updated_at", table_name="commercial_cluster_registry"
    )
    op.drop_index(
        "ix_commercial_cluster_registry_created_at", table_name="commercial_cluster_registry"
    )
    op.drop_index(
        "ix_commercial_cluster_registry_last_seen_at", table_name="commercial_cluster_registry"
    )
    op.drop_index(
        "ix_commercial_cluster_registry_priority", table_name="commercial_cluster_registry"
    )
    op.drop_index("ix_commercial_cluster_registry_status", table_name="commercial_cluster_registry")
    op.drop_index(
        "ix_commercial_cluster_registry_environment", table_name="commercial_cluster_registry"
    )
    op.drop_index("ix_commercial_cluster_registry_region", table_name="commercial_cluster_registry")
    op.drop_index(
        "ix_commercial_cluster_registry_cluster_id", table_name="commercial_cluster_registry"
    )
    op.drop_table("commercial_cluster_registry")
