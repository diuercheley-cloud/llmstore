"""commercial ha leader election

Revision ID: 20260514_0037
Revises: 20260514_0036
Create Date: 2026-05-14 16:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0037"
down_revision = "20260514_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_leader_leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", sa.String(length=128), nullable=False),
        sa.Column("leader_role", sa.String(length=32), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("lease_token", sa.BigInteger(), nullable=False),
        sa.Column("lease_acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_leader_leases_cluster_id", "commercial_leader_leases", ["cluster_id"], unique=False)
    op.create_index("ix_commercial_leader_leases_leader_role", "commercial_leader_leases", ["leader_role"], unique=False)
    op.create_index("ix_commercial_leader_leases_node_id", "commercial_leader_leases", ["node_id"], unique=False)
    op.create_index("ix_commercial_leader_leases_lease_token", "commercial_leader_leases", ["lease_token"], unique=False)
    op.create_index("ix_commercial_leader_leases_lease_expires_at", "commercial_leader_leases", ["lease_expires_at"], unique=False)
    op.create_index("ix_commercial_leader_leases_last_heartbeat_at", "commercial_leader_leases", ["last_heartbeat_at"], unique=False)
    op.create_index("ix_commercial_leader_leases_status", "commercial_leader_leases", ["status"], unique=False)
    op.create_index(
        "uq_commercial_leader_leases_active_role",
        "commercial_leader_leases",
        ["cluster_id", "leader_role"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_commercial_leader_leases_active_role", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_status", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_last_heartbeat_at", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_lease_expires_at", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_lease_token", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_node_id", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_leader_role", table_name="commercial_leader_leases")
    op.drop_index("ix_commercial_leader_leases_cluster_id", table_name="commercial_leader_leases")
    op.drop_table("commercial_leader_leases")
