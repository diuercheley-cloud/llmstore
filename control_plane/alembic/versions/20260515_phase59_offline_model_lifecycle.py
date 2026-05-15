"""phase59_offline_model_lifecycle

Revision ID: 20260515_phase59
Revises: 20260515_phase58
Create Date: 2026-05-15 23:59:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_phase59"
down_revision = "20260515_phase58"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def _uuid_type():
    return postgresql.UUID(as_uuid=True) if _dialect_name() == "postgresql" else sa.String(length=36)


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if _dialect_name() == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "commercial_model_lifecycle_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("registry_entry_id", _uuid_type(), nullable=True, index=True),
        sa.Column("model_name", sa.String(length=255), nullable=False, index=True),
        sa.Column("model_alias", sa.String(length=128), nullable=True, index=True),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("provider", sa.String(length=128), nullable=True, index=True),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=True, index=True),
        sa.Column("manifest_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, index=True),
        sa.Column("previous_lifecycle_state", sa.String(length=32), nullable=True, index=True),
        sa.Column("tenant_scope_json", _json_type(), nullable=True),
        sa.Column("provenance_id", _uuid_type(), nullable=True, index=True),
        sa.Column("attestation_bound", sa.Boolean(), nullable=False),
        sa.Column("checksum_verified", sa.Boolean(), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False),
        sa.Column("lineage_validated", sa.Boolean(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("sovereign_restricted", sa.Boolean(), nullable=False),
        sa.Column("export_restricted", sa.Boolean(), nullable=False),
        sa.Column("cluster_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("node_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("metadata_json", _json_type(), nullable=True),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["registry_entry_id"], ["commercial_signed_model_registry_entries.id"]),
        sa.ForeignKeyConstraint(["provenance_id"], ["commercial_model_provenance_attestations.id"]),
    )
    op.create_index("ix_lifecycle_records_model_state", "commercial_model_lifecycle_records", ["model_name", "lifecycle_state"], unique=False)
    op.create_index("ix_lifecycle_records_cluster_state", "commercial_model_lifecycle_records", ["cluster_id", "lifecycle_state"], unique=False)

    op.create_table(
        "commercial_model_promotion_requests",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("lifecycle_record_id", _uuid_type(), nullable=False, index=True),
        sa.Column("request_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("requested_by", sa.String(length=255), nullable=True),
        sa.Column("target_state", sa.String(length=32), nullable=False, index=True),
        sa.Column("source_state", sa.String(length=32), nullable=False, index=True),
        sa.Column("approval_count_required", sa.Integer(), nullable=False),
        sa.Column("approval_count_received", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, index=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("bundle_id", _uuid_type(), nullable=True, index=True),
        sa.Column("approval_json", _json_type(), nullable=True),
        sa.Column("signed_manifest_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column("immutable_receipt_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column("media_ref", sa.String(length=512), nullable=True),
        sa.Column("chain_of_custody_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lifecycle_record_id"], ["commercial_model_lifecycle_records.id"]),
        sa.ForeignKeyConstraint(["bundle_id"], ["commercial_model_promotion_bundles.id"]),
    )
    op.create_index("ix_promotion_requests_status", "commercial_model_promotion_requests", ["status", "target_state"], unique=False)

    op.create_table(
        "commercial_model_lineages",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("lifecycle_record_id", _uuid_type(), nullable=False, index=True),
        sa.Column("parent_lineage_id", _uuid_type(), nullable=True, index=True),
        sa.Column("source_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("source_ref", sa.String(length=512), nullable=True),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("derivation_method", sa.String(length=32), nullable=False, index=True),
        sa.Column("artifact_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("predecessor_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("provenance_id", _uuid_type(), nullable=True, index=True),
        sa.Column("evidence_json", _json_type(), nullable=True),
        sa.Column("dag_node_json", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lifecycle_record_id"], ["commercial_model_lifecycle_records.id"]),
        sa.ForeignKeyConstraint(["parent_lineage_id"], ["commercial_model_lineages.id"]),
        sa.ForeignKeyConstraint(["provenance_id"], ["commercial_model_provenance_attestations.id"]),
    )
    op.create_index("ix_model_lineages_hash_chain", "commercial_model_lineages", ["artifact_hash", "predecessor_hash"], unique=False)
    op.create_index("ix_model_lineages_depth", "commercial_model_lineages", ["lifecycle_record_id", "depth"], unique=False)

    op.create_table(
        "commercial_model_rollback_records",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("lifecycle_record_id", _uuid_type(), nullable=False, index=True),
        sa.Column("promotion_request_id", _uuid_type(), nullable=True, index=True),
        sa.Column("rollback_from_state", sa.String(length=32), nullable=False, index=True),
        sa.Column("rollback_to_state", sa.String(length=32), nullable=False, index=True),
        sa.Column("rollback_reason", sa.Text(), nullable=False),
        sa.Column("rolled_back_by", sa.String(length=255), nullable=True),
        sa.Column("verification_hash", sa.String(length=128), nullable=False, index=True),
        sa.Column("predecessor_checksum", sa.String(length=128), nullable=True, index=True),
        sa.Column("checksum_verified", sa.Boolean(), nullable=False),
        sa.Column("lineage_valid", sa.Boolean(), nullable=False),
        sa.Column("attestation_valid", sa.Boolean(), nullable=False),
        sa.Column("chain_of_custody_json", _json_type(), nullable=True),
        sa.Column("immutable_receipt_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lifecycle_record_id"], ["commercial_model_lifecycle_records.id"]),
        sa.ForeignKeyConstraint(["promotion_request_id"], ["commercial_model_promotion_requests.id"]),
    )

    op.create_table(
        "commercial_offline_model_verifications",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("lifecycle_record_id", _uuid_type(), nullable=True, index=True),
        sa.Column("verification_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("model_name", sa.String(length=255), nullable=False, index=True),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=True, index=True),
        sa.Column("manifest_hash", sa.String(length=128), nullable=True, index=True),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("checksum_valid", sa.Boolean(), nullable=False),
        sa.Column("provenance_valid", sa.Boolean(), nullable=False),
        sa.Column("crl_valid", sa.Boolean(), nullable=False),
        sa.Column("attestation_valid", sa.Boolean(), nullable=False),
        sa.Column("lineage_valid", sa.Boolean(), nullable=False),
        sa.Column("overall_valid", sa.Boolean(), nullable=False, index=True),
        sa.Column("media_ref", sa.String(length=512), nullable=True),
        sa.Column("media_uuid", sa.String(length=128), nullable=True),
        sa.Column("source_cluster_id", sa.String(length=255), nullable=True, index=True),
        sa.Column("signed_manifest", _json_type(), nullable=True),
        sa.Column("verification_details_json", _json_type(), nullable=True),
        sa.Column("verified_by", sa.String(length=255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lifecycle_record_id"], ["commercial_model_lifecycle_records.id"]),
    )
    op.create_index("ix_offline_model_verifications_lookup", "commercial_offline_model_verifications", ["model_name", "verification_type", "overall_valid"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_offline_model_verifications_lookup", table_name="commercial_offline_model_verifications")
    op.drop_table("commercial_offline_model_verifications")
    op.drop_table("commercial_model_rollback_records")
    op.drop_index("ix_model_lineages_depth", table_name="commercial_model_lineages")
    op.drop_index("ix_model_lineages_hash_chain", table_name="commercial_model_lineages")
    op.drop_table("commercial_model_lineages")
    op.drop_index("ix_promotion_requests_status", table_name="commercial_model_promotion_requests")
    op.drop_table("commercial_model_promotion_requests")
    op.drop_index("ix_lifecycle_records_cluster_state", table_name="commercial_model_lifecycle_records")
    op.drop_index("ix_lifecycle_records_model_state", table_name="commercial_model_lifecycle_records")
    op.drop_table("commercial_model_lifecycle_records")
