"""repair missing witness and transparency tables

Revision ID: 20260518_0082
Revises: phase81_reproducible_builds
Create Date: 2026-05-18 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_0082"
down_revision = "phase81_reproducible_builds"
branch_labels = None
depends_on = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names(schema="public")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_witnesses"):
        op.create_table(
            "commercial_witnesses",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("witness_name", sa.String(length=255), nullable=False),
            sa.Column("witness_type", sa.String(length=50), nullable=False),
            sa.Column("public_key", sa.Text(), nullable=True),
            sa.Column("endpoint", sa.String(length=512), nullable=True),
            sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
            sa.Column("trust_level", sa.String(length=50), server_default="medium", nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_witness_quorum_policies"):
        op.create_table(
            "commercial_witness_quorum_policies",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("timeline_type", sa.String(length=100), nullable=False),
            sa.Column("required_signatures", sa.Integer(), server_default="1", nullable=False),
            sa.Column("allowed_witnesses_json", sa.JSON(), nullable=True),
            sa.Column(
                "require_external_witness", sa.Boolean(), server_default="false", nullable=False
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_witness_signatures"):
        op.create_table(
            "commercial_witness_signatures",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("timeline_id", sa.UUID(), nullable=False),
            sa.Column("witness_id", sa.UUID(), nullable=False),
            sa.Column("merkle_root", sa.String(length=255), nullable=False),
            sa.Column("signature", sa.Text(), nullable=False),
            sa.Column("signature_algorithm", sa.String(length=50), nullable=False),
            sa.Column("signed_at", sa.DateTime(), nullable=False),
            sa.Column(
                "verification_status",
                sa.String(length=50),
                server_default="pending",
                nullable=False,
            ),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["timeline_id"], ["commercial_merkle_timelines.id"]),
            sa.ForeignKeyConstraint(["witness_id"], ["commercial_witnesses.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_witness_audit_events"):
        op.create_table(
            "commercial_witness_audit_events",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("witness_id", sa.UUID(), nullable=True),
            sa.Column("timeline_id", sa.UUID(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("immutable_hash", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_transparency_gossip_peers"):
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
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_transparency_gossip_records"):
        op.create_table(
            "commercial_transparency_gossip_records",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("source_peer_id", sa.String(length=255), nullable=False),
            sa.Column("target_peer_id", sa.String(length=255), nullable=True),
            sa.Column("timeline_root", sa.String(length=255), nullable=True),
            sa.Column("timeline_hash", sa.String(length=255), nullable=True),
            sa.Column("checkpoint_hash", sa.String(length=255), nullable=True),
            sa.Column("gossip_type", sa.String(length=50), nullable=False),
            sa.Column(
                "verification_status",
                sa.String(length=50),
                server_default="unknown",
                nullable=False,
            ),
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
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_consistency_checkpoints"):
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
        inspector = sa.inspect(bind)

    if not _has_table(inspector, "commercial_transparency_split_view_alerts"):
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
    pass
