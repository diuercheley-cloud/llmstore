"""phase45_transparency_gossip

Revision ID: e526a1282b29
Revises: 4dae4ba9d504
Create Date: 2026-05-15 12:57:45.829920
"""
import sqlalchemy as sa
from alembic import op

revision = 'e526a1282b29'
down_revision = '4dae4ba9d504'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_transparency_gossip_peers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("peer_id", sa.String(length=255), nullable=False),
        sa.Column("peer_type", sa.String(length=50), nullable=False),
        sa.Column("endpoint", sa.String(length=512), nullable=True),
        sa.Column("public_key", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("peer_id"),
    )
    op.create_index(
        "ix_commercial_transparency_gossip_peers_peer_id",
        "commercial_transparency_gossip_peers",
        ["peer_id"],
        unique=False,
    )

    op.create_table(
        "commercial_transparency_gossip_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_peer_id", sa.String(length=255), nullable=False),
        sa.Column("target_peer_id", sa.String(length=255), nullable=True),
        sa.Column("timeline_root", sa.String(length=255), nullable=True),
        sa.Column("timeline_hash", sa.String(length=255), nullable=True),
        sa.Column("checkpoint_hash", sa.String(length=255), nullable=True),
        sa.Column("gossip_type", sa.String(length=50), nullable=False),
        sa.Column("verification_status", sa.String(length=50), server_default="unknown", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_transparency_gossip_records_source_peer_id",
        "commercial_transparency_gossip_records",
        ["source_peer_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_transparency_gossip_records_target_peer_id",
        "commercial_transparency_gossip_records",
        ["target_peer_id"],
        unique=False,
    )

    op.create_table(
        "commercial_consistency_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("checkpoint_type", sa.String(length=50), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("root_hash", sa.String(length=255), nullable=False),
        sa.Column("signed_checkpoint", sa.String(length=1024), nullable=True),
        sa.Column("witness_summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_consistency_checkpoints_root_hash",
        "commercial_consistency_checkpoints",
        ["root_hash"],
        unique=False,
    )

    op.create_table(
        "commercial_transparency_split_view_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alert_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("expected_hash", sa.String(length=255), nullable=True),
        sa.Column("observed_hash", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.String(length=1024), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("commercial_transparency_split_view_alerts")
    op.drop_index("ix_commercial_consistency_checkpoints_root_hash", table_name="commercial_consistency_checkpoints")
    op.drop_table("commercial_consistency_checkpoints")
    op.drop_index("ix_commercial_transparency_gossip_records_target_peer_id", table_name="commercial_transparency_gossip_records")
    op.drop_index("ix_commercial_transparency_gossip_records_source_peer_id", table_name="commercial_transparency_gossip_records")
    op.drop_table("commercial_transparency_gossip_records")
    op.drop_index("ix_commercial_transparency_gossip_peers_peer_id", table_name="commercial_transparency_gossip_peers")
    op.drop_table("commercial_transparency_gossip_peers")
