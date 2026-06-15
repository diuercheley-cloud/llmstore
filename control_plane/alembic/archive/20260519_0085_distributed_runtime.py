"""distributed runtime

Revision ID: 20260519_0085
Revises: 20260518_0084
Create Date: 2026-05-19 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260519_0085"
down_revision: Union[str, None] = "20260518_0084"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # runtime_nodes
    op.create_table(
        "runtime_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=1024), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=True),
        sa.Column("gpu_count", sa.Integer(), nullable=True),
        sa.Column("gpu_memory_total_mb", sa.Integer(), nullable=True),
        sa.Column("cpu_count", sa.Integer(), nullable=True),
        sa.Column("memory_total_mb", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trust_level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # runtime_node_heartbeats
    op.create_table(
        "runtime_node_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cpu_usage_percent", sa.Float(), nullable=True),
        sa.Column("memory_usage_mb", sa.Float(), nullable=True),
        sa.Column("gpu_usage_percent", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active_requests", sa.Integer(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["runtime_nodes.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_runtime_node_heartbeats_node_id"),
        "runtime_node_heartbeats",
        ["node_id"],
        unique=False,
    )

    # runtime_model_placements
    op.create_table(
        "runtime_model_placements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["model_registry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["runtime_nodes.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_runtime_model_placements_model_id"),
        "runtime_model_placements",
        ["model_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_model_placements_node_id"),
        "runtime_model_placements",
        ["node_id"],
        unique=False,
    )

    # runtime_routing_events
    op.create_table(
        "runtime_routing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routing_strategy", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["model_registry.id"],
        ),
        sa.ForeignKeyConstraint(
            ["selected_node_id"],
            ["runtime_nodes.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_runtime_routing_events_request_id"),
        "runtime_routing_events",
        ["request_id"],
        unique=False,
    )

    # runtime_failover_events
    op.create_table(
        "runtime_failover_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("failed_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["failed_node_id"],
            ["runtime_nodes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"],
            ["runtime_nodes.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_runtime_failover_events_request_id"),
        "runtime_failover_events",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("runtime_failover_events")
    op.drop_table("runtime_routing_events")
    op.drop_table("runtime_model_placements")
    op.drop_table("runtime_node_heartbeats")
    op.drop_table("runtime_nodes")
