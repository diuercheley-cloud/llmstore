"""Add Commercial Global Traffic Shifting

Revision ID: 20260514_0038
Revises: a9c32628411c
Create Date: 2026-05-14 16:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260514_0038"
down_revision = "a9c32628411c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_global_traffic_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("source_cluster_id", sa.String(), nullable=False),
        sa.Column("target_cluster_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("traffic_percent", sa.Integer(), nullable=False),
        sa.Column("max_traffic_percent", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, default="pending"),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "commercial_global_traffic_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("policy_id", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("client_id", sa.String(), nullable=True),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("selected_cluster_id", sa.String(), nullable=False),
        sa.Column("original_cluster_id", sa.String(), nullable=False),
        sa.Column("target_cluster_id", sa.String(), nullable=True),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("bucket", sa.Integer(), nullable=False),
        sa.Column("traffic_percent", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("commercial_global_traffic_decisions")
    op.drop_table("commercial_global_traffic_policies")
