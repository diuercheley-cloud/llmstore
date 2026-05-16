"""Add Phase 77 sovereign federation synchronization protocol

Revision ID: phase77_federation_sync_protocol
Revises: phase76_attestation_framework
Create Date: 2026-05-16 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "phase77_federation_sync_protocol"
down_revision = "phase76_attestation_framework"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sovereign_federation_environments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("environment_name", sa.String(length=120), nullable=False),
        sa.Column("environment_type", sa.String(length=64), nullable=False),
        sa.Column("federation_scope", sa.String(length=255), nullable=False),
        sa.Column("trust_level", sa.String(length=32), nullable=False),
        sa.Column("offline_only", sa.Boolean(), nullable=False),
        sa.Column("deterministic_version", sa.String(length=32), nullable=False),
        sa.Column("environment_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sovereign_federation_environments_client_id"), "sovereign_federation_environments", ["client_id"], unique=False)
    op.create_index(op.f("ix_sovereign_federation_environments_environment_name"), "sovereign_federation_environments", ["environment_name"], unique=False)
    op.create_index(op.f("ix_sovereign_federation_environments_environment_type"), "sovereign_federation_environments", ["environment_type"], unique=False)
    op.create_index(op.f("ix_sovereign_federation_environments_trust_level"), "sovereign_federation_environments", ["trust_level"], unique=False)
    op.create_index(op.f("ix_sovereign_federation_environments_environment_hash"), "sovereign_federation_environments", ["environment_hash"], unique=True)
    op.create_index(op.f("ix_sovereign_federation_environments_immutable_hash"), "sovereign_federation_environments", ["immutable_hash"], unique=True)

    op.create_table(
        "federation_synchronization_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("source_environment_id", sa.String(length=64), nullable=False),
        sa.Column("target_environment_id", sa.String(length=64), nullable=False),
        sa.Column("sync_scope", sa.String(length=255), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("offline_verifiable", sa.Boolean(), nullable=False),
        sa.Column("lineage_verified", sa.Boolean(), nullable=False),
        sa.Column("deterministic_version", sa.String(length=32), nullable=False),
        sa.Column("session_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_environment_id"], ["sovereign_federation_environments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_environment_id"], ["sovereign_federation_environments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_synchronization_sessions_client_id"), "federation_synchronization_sessions", ["client_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_sessions_source_environment_id"), "federation_synchronization_sessions", ["source_environment_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_sessions_target_environment_id"), "federation_synchronization_sessions", ["target_environment_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_sessions_sync_status"), "federation_synchronization_sessions", ["sync_status"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_sessions_session_hash"), "federation_synchronization_sessions", ["session_hash"], unique=True)
    op.create_index(op.f("ix_federation_synchronization_sessions_immutable_hash"), "federation_synchronization_sessions", ["immutable_hash"], unique=True)

    op.create_table(
        "federation_synchronization_bundles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("bundle_name", sa.String(length=120), nullable=False),
        sa.Column("bundle_type", sa.String(length=32), nullable=False),
        sa.Column("bundle_hash", sa.String(length=64), nullable=False),
        sa.Column("lineage_hash", sa.String(length=64), nullable=False),
        sa.Column("parent_bundle_hash", sa.String(length=64), nullable=True),
        sa.Column("replay_hash", sa.String(length=64), nullable=False),
        sa.Column("bundle_status", sa.String(length=32), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["federation_synchronization_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_synchronization_bundles_client_id"), "federation_synchronization_bundles", ["client_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_session_id"), "federation_synchronization_bundles", ["session_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_bundle_type"), "federation_synchronization_bundles", ["bundle_type"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_bundle_hash"), "federation_synchronization_bundles", ["bundle_hash"], unique=True)
    op.create_index(op.f("ix_federation_synchronization_bundles_lineage_hash"), "federation_synchronization_bundles", ["lineage_hash"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_parent_bundle_hash"), "federation_synchronization_bundles", ["parent_bundle_hash"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_replay_hash"), "federation_synchronization_bundles", ["replay_hash"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_bundle_status"), "federation_synchronization_bundles", ["bundle_status"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_bundles_immutable_hash"), "federation_synchronization_bundles", ["immutable_hash"], unique=True)

    op.create_table(
        "federation_trust_negotiations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("source_environment_id", sa.String(length=64), nullable=False),
        sa.Column("target_environment_id", sa.String(length=64), nullable=False),
        sa.Column("negotiation_status", sa.String(length=32), nullable=False),
        sa.Column("required_trust_level", sa.String(length=32), nullable=False),
        sa.Column("negotiated_trust_level", sa.String(length=32), nullable=False),
        sa.Column("replay_verification_required", sa.Boolean(), nullable=False),
        sa.Column("offline_verification_required", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_environment_id"], ["sovereign_federation_environments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_environment_id"], ["sovereign_federation_environments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_trust_negotiations_client_id"), "federation_trust_negotiations", ["client_id"], unique=False)
    op.create_index(op.f("ix_federation_trust_negotiations_source_environment_id"), "federation_trust_negotiations", ["source_environment_id"], unique=False)
    op.create_index(op.f("ix_federation_trust_negotiations_target_environment_id"), "federation_trust_negotiations", ["target_environment_id"], unique=False)
    op.create_index(op.f("ix_federation_trust_negotiations_negotiation_status"), "federation_trust_negotiations", ["negotiation_status"], unique=False)
    op.create_index(op.f("ix_federation_trust_negotiations_immutable_hash"), "federation_trust_negotiations", ["immutable_hash"], unique=True)

    op.create_table(
        "federation_conflict_resolutions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("conflict_type", sa.String(length=32), nullable=False),
        sa.Column("resolution_strategy", sa.String(length=32), nullable=False),
        sa.Column("resolution_status", sa.String(length=32), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["federation_synchronization_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_conflict_resolutions_client_id"), "federation_conflict_resolutions", ["client_id"], unique=False)
    op.create_index(op.f("ix_federation_conflict_resolutions_session_id"), "federation_conflict_resolutions", ["session_id"], unique=False)
    op.create_index(op.f("ix_federation_conflict_resolutions_conflict_type"), "federation_conflict_resolutions", ["conflict_type"], unique=False)
    op.create_index(op.f("ix_federation_conflict_resolutions_resolution_status"), "federation_conflict_resolutions", ["resolution_status"], unique=False)
    op.create_index(op.f("ix_federation_conflict_resolutions_immutable_hash"), "federation_conflict_resolutions", ["immutable_hash"], unique=True)

    op.create_table(
        "federation_synchronization_receipts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["federation_synchronization_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_synchronization_receipts_client_id"), "federation_synchronization_receipts", ["client_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_receipts_session_id"), "federation_synchronization_receipts", ["session_id"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_receipts_payload_hash"), "federation_synchronization_receipts", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_federation_synchronization_receipts_immutable_hash"), "federation_synchronization_receipts", ["immutable_hash"], unique=True)

    op.create_table(
        "federation_lineage_links",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("bundle_id", sa.String(length=64), nullable=False),
        sa.Column("parent_bundle_hash", sa.String(length=64), nullable=True),
        sa.Column("lineage_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["federation_synchronization_bundles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_lineage_links_client_id"), "federation_lineage_links", ["client_id"], unique=False)
    op.create_index(op.f("ix_federation_lineage_links_bundle_id"), "federation_lineage_links", ["bundle_id"], unique=False)
    op.create_index(op.f("ix_federation_lineage_links_parent_bundle_hash"), "federation_lineage_links", ["parent_bundle_hash"], unique=False)
    op.create_index(op.f("ix_federation_lineage_links_lineage_hash"), "federation_lineage_links", ["lineage_hash"], unique=False)
    op.create_index(op.f("ix_federation_lineage_links_immutable_hash"), "federation_lineage_links", ["immutable_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("federation_lineage_links")
    op.drop_table("federation_synchronization_receipts")
    op.drop_table("federation_conflict_resolutions")
    op.drop_table("federation_trust_negotiations")
    op.drop_table("federation_synchronization_bundles")
    op.drop_table("federation_synchronization_sessions")
    op.drop_table("sovereign_federation_environments")
