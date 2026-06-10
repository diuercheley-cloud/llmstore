"""enterprise_multi_region_governance_federation

Revision ID: 20260514_0053
Revises: 20260514_0052
Create Date: 2026-05-14 23:59:31.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0053"
down_revision = "20260514_0052"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_governance_federation_peers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("peer_cluster_id", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sync_mode", sa.String(length=32), nullable=False),
        sa.Column("trust_level", sa.String(length=32), nullable=False),
        sa.Column("last_policy_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_audit_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_governance_federation_peers_peer_cluster_id"),
        "commercial_governance_federation_peers",
        ["peer_cluster_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_commercial_governance_federation_peers_status"),
        "commercial_governance_federation_peers",
        ["status"],
        unique=False,
    )

    op.create_table(
        "commercial_federated_policy_syncs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=False),
        sa.Column("target_cluster_id", sa.String(length=255), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bundle_name", sa.String(length=255), nullable=False),
        sa.Column("bundle_version", sa.String(length=64), nullable=False),
        sa.Column("sync_direction", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("target_hash", sa.String(length=64), nullable=True),
        sa.Column("records_synced", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_federated_policy_syncs_source_cluster_id"),
        "commercial_federated_policy_syncs",
        ["source_cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_federated_policy_syncs_target_cluster_id"),
        "commercial_federated_policy_syncs",
        ["target_cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_federated_policy_syncs_status"),
        "commercial_federated_policy_syncs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "commercial_federated_audit_trails",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=False),
        sa.Column("source_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("event_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_federated_audit_trails_dedupe_key"),
        "commercial_federated_audit_trails",
        ["dedupe_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_commercial_federated_audit_trails_event_type"),
        "commercial_federated_audit_trails",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_federated_audit_trails_source_cluster_id"),
        "commercial_federated_audit_trails",
        ["source_cluster_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("commercial_federated_audit_trails")
    op.drop_table("commercial_federated_policy_syncs")
    op.drop_table("commercial_governance_federation_peers")
