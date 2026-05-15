"""add commercial routing config

Revision ID: 20260514_0032
Revises: 20260514_0031
Create Date: 2026-05-14 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0032"
down_revision = "20260514_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_routing_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("cost_multiplier", sa.Float(), nullable=False),
        sa.Column("margin_weight", sa.Float(), nullable=False),
        sa.Column("latency_weight", sa.Float(), nullable=False),
        sa.Column("quality_weight", sa.Float(), nullable=False),
        sa.Column("local_route_bonus", sa.Float(), nullable=False),
        sa.Column("min_margin_percent", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_routing_config_scope_type", "commercial_routing_config", ["scope_type"])
    op.create_index("ix_commercial_routing_config_provider", "commercial_routing_config", ["provider"])
    op.create_index("ix_commercial_routing_config_model", "commercial_routing_config", ["model"])
    op.create_index("ix_commercial_routing_config_is_active", "commercial_routing_config", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_commercial_routing_config_is_active", table_name="commercial_routing_config")
    op.drop_index("ix_commercial_routing_config_model", table_name="commercial_routing_config")
    op.drop_index("ix_commercial_routing_config_provider", table_name="commercial_routing_config")
    op.drop_index("ix_commercial_routing_config_scope_type", table_name="commercial_routing_config")
    op.drop_table("commercial_routing_config")
