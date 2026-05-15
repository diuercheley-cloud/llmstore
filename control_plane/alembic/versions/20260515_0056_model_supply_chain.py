"""Phase 38 model supply chain

Revision ID: 20260515_0056
Revises: 20260515_0055
Create Date: 2026-05-15 01:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0056"
down_revision = "20260515_0055"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_model_provenance_attestations",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=True),
        sa.Column("imported_by", sa.String(length=255), nullable=True),
        sa.Column("import_method", sa.String(length=32), nullable=False),
        sa.Column("artifact_hash", sa.String(length=128), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("chain_of_custody_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_model_provenance_attestations_source_type"), "commercial_model_provenance_attestations", ["source_type"], unique=False)
    op.create_index(op.f("ix_commercial_model_provenance_attestations_source_cluster_id"), "commercial_model_provenance_attestations", ["source_cluster_id"], unique=False)
    op.create_index(op.f("ix_commercial_model_provenance_attestations_import_method"), "commercial_model_provenance_attestations", ["import_method"], unique=False)
    op.create_index(op.f("ix_commercial_model_provenance_attestations_artifact_hash"), "commercial_model_provenance_attestations", ["artifact_hash"], unique=False)

    op.create_table(
        "commercial_signed_model_registry_entries",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_alias", sa.String(length=128), nullable=True),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("model_file_path", sa.String(length=512), nullable=True),
        sa.Column("model_format", sa.String(length=32), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("provenance_id", _uuid_type(), nullable=True),
        sa.Column("trust_state", sa.String(length=32), nullable=False),
        sa.Column("tenant_scope_json", sa.JSON(), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provenance_id"], ["commercial_model_provenance_attestations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_model_name"), "commercial_signed_model_registry_entries", ["model_name"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_model_alias"), "commercial_signed_model_registry_entries", ["model_alias"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_provider"), "commercial_signed_model_registry_entries", ["provider"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_model_format"), "commercial_signed_model_registry_entries", ["model_format"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_checksum_sha256"), "commercial_signed_model_registry_entries", ["checksum_sha256"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_manifest_hash"), "commercial_signed_model_registry_entries", ["manifest_hash"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_provenance_id"), "commercial_signed_model_registry_entries", ["provenance_id"], unique=False)
    op.create_index(op.f("ix_commercial_signed_model_registry_entries_trust_state"), "commercial_signed_model_registry_entries", ["trust_state"], unique=False)

    op.create_table(
        "commercial_model_revocation_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("registry_entry_id", _uuid_type(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("revocation_type", sa.String(length=32), nullable=False),
        sa.Column("revoked_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["registry_entry_id"], ["commercial_signed_model_registry_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_model_revocation_records_registry_entry_id"), "commercial_model_revocation_records", ["registry_entry_id"], unique=False)
    op.create_index(op.f("ix_commercial_model_revocation_records_model_name"), "commercial_model_revocation_records", ["model_name"], unique=False)
    op.create_index(op.f("ix_commercial_model_revocation_records_revocation_type"), "commercial_model_revocation_records", ["revocation_type"], unique=False)

    op.create_table(
        "commercial_model_promotion_bundles",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("bundle_name", sa.String(length=255), nullable=False),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=True),
        sa.Column("target_cluster_id", sa.String(length=255), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_model_promotion_bundles_bundle_name"), "commercial_model_promotion_bundles", ["bundle_name"], unique=False)
    op.create_index(op.f("ix_commercial_model_promotion_bundles_source_cluster_id"), "commercial_model_promotion_bundles", ["source_cluster_id"], unique=False)
    op.create_index(op.f("ix_commercial_model_promotion_bundles_target_cluster_id"), "commercial_model_promotion_bundles", ["target_cluster_id"], unique=False)
    op.create_index(op.f("ix_commercial_model_promotion_bundles_manifest_hash"), "commercial_model_promotion_bundles", ["manifest_hash"], unique=False)
    op.create_index(op.f("ix_commercial_model_promotion_bundles_status"), "commercial_model_promotion_bundles", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commercial_model_promotion_bundles_status"), table_name="commercial_model_promotion_bundles")
    op.drop_index(op.f("ix_commercial_model_promotion_bundles_manifest_hash"), table_name="commercial_model_promotion_bundles")
    op.drop_index(op.f("ix_commercial_model_promotion_bundles_target_cluster_id"), table_name="commercial_model_promotion_bundles")
    op.drop_index(op.f("ix_commercial_model_promotion_bundles_source_cluster_id"), table_name="commercial_model_promotion_bundles")
    op.drop_index(op.f("ix_commercial_model_promotion_bundles_bundle_name"), table_name="commercial_model_promotion_bundles")
    op.drop_table("commercial_model_promotion_bundles")

    op.drop_index(op.f("ix_commercial_model_revocation_records_revocation_type"), table_name="commercial_model_revocation_records")
    op.drop_index(op.f("ix_commercial_model_revocation_records_model_name"), table_name="commercial_model_revocation_records")
    op.drop_index(op.f("ix_commercial_model_revocation_records_registry_entry_id"), table_name="commercial_model_revocation_records")
    op.drop_table("commercial_model_revocation_records")

    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_trust_state"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_provenance_id"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_manifest_hash"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_checksum_sha256"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_model_format"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_provider"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_model_alias"), table_name="commercial_signed_model_registry_entries")
    op.drop_index(op.f("ix_commercial_signed_model_registry_entries_model_name"), table_name="commercial_signed_model_registry_entries")
    op.drop_table("commercial_signed_model_registry_entries")

    op.drop_index(op.f("ix_commercial_model_provenance_attestations_artifact_hash"), table_name="commercial_model_provenance_attestations")
    op.drop_index(op.f("ix_commercial_model_provenance_attestations_import_method"), table_name="commercial_model_provenance_attestations")
    op.drop_index(op.f("ix_commercial_model_provenance_attestations_source_cluster_id"), table_name="commercial_model_provenance_attestations")
    op.drop_index(op.f("ix_commercial_model_provenance_attestations_source_type"), table_name="commercial_model_provenance_attestations")
    op.drop_table("commercial_model_provenance_attestations")
