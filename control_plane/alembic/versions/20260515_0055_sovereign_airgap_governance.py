"""Phase 37 sovereign airgap governance

Revision ID: 20260515_0055
Revises: 20260514_0054
Create Date: 2026-05-15 00:55:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0055"
down_revision = "20260514_0054"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_airgap_sync_packages",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("package_type", sa.String(length=64), nullable=False),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=False),
        sa.Column("target_cluster_id", sa.String(length=255), nullable=True),
        sa.Column("package_version", sa.String(length=64), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("encryption_key_id", _uuid_type(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_ref", sa.String(length=512), nullable=True),
        sa.Column("chain_of_custody_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_airgap_sync_packages_package_type"), "commercial_airgap_sync_packages", ["package_type"], unique=False)
    op.create_index(op.f("ix_commercial_airgap_sync_packages_source_cluster_id"), "commercial_airgap_sync_packages", ["source_cluster_id"], unique=False)
    op.create_index(op.f("ix_commercial_airgap_sync_packages_target_cluster_id"), "commercial_airgap_sync_packages", ["target_cluster_id"], unique=False)
    op.create_index(op.f("ix_commercial_airgap_sync_packages_manifest_hash"), "commercial_airgap_sync_packages", ["manifest_hash"], unique=False)
    op.create_index(op.f("ix_commercial_airgap_sync_packages_encryption_key_id"), "commercial_airgap_sync_packages", ["encryption_key_id"], unique=False)
    op.create_index(op.f("ix_commercial_airgap_sync_packages_status"), "commercial_airgap_sync_packages", ["status"], unique=False)

    op.create_table(
        "commercial_offline_revocation_lists",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("crl_version", sa.String(length=64), nullable=False),
        sa.Column("revoked_key_fingerprints_json", sa.JSON(), nullable=False),
        sa.Column("revoked_bundle_hashes_json", sa.JSON(), nullable=False),
        sa.Column("revoked_peer_ids_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_offline_revocation_lists_manifest_hash"), "commercial_offline_revocation_lists", ["manifest_hash"], unique=False)

    op.create_table(
        "commercial_hardware_attestation_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("node_id", sa.String(length=255), nullable=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=False),
        sa.Column("attestation_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("evidence_hash", sa.String(length=128), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_hardware_attestation_records_node_id"), "commercial_hardware_attestation_records", ["node_id"], unique=False)
    op.create_index(op.f("ix_commercial_hardware_attestation_records_cluster_id"), "commercial_hardware_attestation_records", ["cluster_id"], unique=False)
    op.create_index(op.f("ix_commercial_hardware_attestation_records_attestation_type"), "commercial_hardware_attestation_records", ["attestation_type"], unique=False)
    op.create_index(op.f("ix_commercial_hardware_attestation_records_status"), "commercial_hardware_attestation_records", ["status"], unique=False)
    op.create_index(op.f("ix_commercial_hardware_attestation_records_evidence_hash"), "commercial_hardware_attestation_records", ["evidence_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commercial_hardware_attestation_records_evidence_hash"), table_name="commercial_hardware_attestation_records")
    op.drop_index(op.f("ix_commercial_hardware_attestation_records_status"), table_name="commercial_hardware_attestation_records")
    op.drop_index(op.f("ix_commercial_hardware_attestation_records_attestation_type"), table_name="commercial_hardware_attestation_records")
    op.drop_index(op.f("ix_commercial_hardware_attestation_records_cluster_id"), table_name="commercial_hardware_attestation_records")
    op.drop_index(op.f("ix_commercial_hardware_attestation_records_node_id"), table_name="commercial_hardware_attestation_records")
    op.drop_table("commercial_hardware_attestation_records")

    op.drop_index(op.f("ix_commercial_offline_revocation_lists_manifest_hash"), table_name="commercial_offline_revocation_lists")
    op.drop_table("commercial_offline_revocation_lists")

    op.drop_index(op.f("ix_commercial_airgap_sync_packages_status"), table_name="commercial_airgap_sync_packages")
    op.drop_index(op.f("ix_commercial_airgap_sync_packages_encryption_key_id"), table_name="commercial_airgap_sync_packages")
    op.drop_index(op.f("ix_commercial_airgap_sync_packages_manifest_hash"), table_name="commercial_airgap_sync_packages")
    op.drop_index(op.f("ix_commercial_airgap_sync_packages_target_cluster_id"), table_name="commercial_airgap_sync_packages")
    op.drop_index(op.f("ix_commercial_airgap_sync_packages_source_cluster_id"), table_name="commercial_airgap_sync_packages")
    op.drop_index(op.f("ix_commercial_airgap_sync_packages_package_type"), table_name="commercial_airgap_sync_packages")
    op.drop_table("commercial_airgap_sync_packages")
