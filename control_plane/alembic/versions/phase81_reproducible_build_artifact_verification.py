"""Add Phase 81 reproducible build artifact verification framework

Revision ID: phase81_reproducible_build_artifact_verification
Revises: phase80_plugin_supply_chain_provenance_sbom
Create Date: 2026-05-16 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "phase81_reproducible_build_artifact_verification"
down_revision = "phase80_plugin_supply_chain_provenance_sbom"
branch_labels = None
depends_on = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.String(length=36)
    return sa.UUID()


def _json_type():
    return sa.JSON()


def upgrade() -> None:
    uuid_type = _uuid_type()
    json_type = _json_type()

    op.create_table(
        "reproducible_build_manifests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("build_name", sa.String(length=120), nullable=False),
        sa.Column("build_scope", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("deterministic_version", sa.String(length=32), nullable=False),
        sa.Column("build_environment_hash", sa.String(length=64), nullable=False),
        sa.Column("build_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("reproducibility_status", sa.String(length=32), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reproducible_build_manifests_client_id"), "reproducible_build_manifests", ["client_id"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_build_name"), "reproducible_build_manifests", ["build_name"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_build_scope"), "reproducible_build_manifests", ["build_scope"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_source_reference"), "reproducible_build_manifests", ["source_reference"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_deterministic_version"), "reproducible_build_manifests", ["deterministic_version"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_build_environment_hash"), "reproducible_build_manifests", ["build_environment_hash"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_build_manifest_hash"), "reproducible_build_manifests", ["build_manifest_hash"], unique=True)
    op.create_index(op.f("ix_reproducible_build_manifests_reproducibility_status"), "reproducible_build_manifests", ["reproducibility_status"], unique=False)
    op.create_index(op.f("ix_reproducible_build_manifests_immutable_hash"), "reproducible_build_manifests", ["immutable_hash"], unique=True)

    op.create_table(
        "artifact_verification_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("build_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_name", sa.String(length=120), nullable=False),
        sa.Column("artifact_version", sa.String(length=32), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("replay_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_manifest_id"], ["reproducible_build_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifact_verification_records_client_id"), "artifact_verification_records", ["client_id"], unique=False)
    op.create_index(op.f("ix_artifact_verification_records_build_manifest_id"), "artifact_verification_records", ["build_manifest_id"], unique=False)
    op.create_index(op.f("ix_artifact_verification_records_artifact_name"), "artifact_verification_records", ["artifact_name"], unique=False)
    op.create_index(op.f("ix_artifact_verification_records_artifact_version"), "artifact_verification_records", ["artifact_version"], unique=False)
    op.create_index(op.f("ix_artifact_verification_records_artifact_hash"), "artifact_verification_records", ["artifact_hash"], unique=False)
    op.create_index(op.f("ix_artifact_verification_records_verification_status"), "artifact_verification_records", ["verification_status"], unique=False)
    op.create_index(op.f("ix_artifact_verification_records_immutable_hash"), "artifact_verification_records", ["immutable_hash"], unique=True)

    op.create_table(
        "source_artifact_lineage",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("build_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("lineage_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_manifest_id"], ["reproducible_build_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_artifact_lineage_client_id"), "source_artifact_lineage", ["client_id"], unique=False)
    op.create_index(op.f("ix_source_artifact_lineage_build_manifest_id"), "source_artifact_lineage", ["build_manifest_id"], unique=False)
    op.create_index(op.f("ix_source_artifact_lineage_source_hash"), "source_artifact_lineage", ["source_hash"], unique=False)
    op.create_index(op.f("ix_source_artifact_lineage_artifact_hash"), "source_artifact_lineage", ["artifact_hash"], unique=False)
    op.create_index(op.f("ix_source_artifact_lineage_lineage_hash"), "source_artifact_lineage", ["lineage_hash"], unique=True)
    op.create_index(op.f("ix_source_artifact_lineage_immutable_hash"), "source_artifact_lineage", ["immutable_hash"], unique=True)

    op.create_table(
        "build_environment_constraints",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("constraint_name", sa.String(length=120), nullable=False),
        sa.Column("constraint_scope", sa.String(length=32), nullable=False),
        sa.Column("required_determinism", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("offline_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("external_network_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("external_dependency_resolution_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_build_environment_constraints_client_id"), "build_environment_constraints", ["client_id"], unique=False)
    op.create_index(op.f("ix_build_environment_constraints_constraint_name"), "build_environment_constraints", ["constraint_name"], unique=False)
    op.create_index(op.f("ix_build_environment_constraints_constraint_scope"), "build_environment_constraints", ["constraint_scope"], unique=False)
    op.create_index(op.f("ix_build_environment_constraints_immutable_hash"), "build_environment_constraints", ["immutable_hash"], unique=True)

    op.create_table(
        "reproducibility_verification_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("build_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("verification_type", sa.String(length=32), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reproducibility_summary", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_manifest_id"], ["reproducible_build_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reproducibility_verification_results_client_id"), "reproducibility_verification_results", ["client_id"], unique=False)
    op.create_index(op.f("ix_reproducibility_verification_results_build_manifest_id"), "reproducibility_verification_results", ["build_manifest_id"], unique=False)
    op.create_index(op.f("ix_reproducibility_verification_results_verification_type"), "reproducibility_verification_results", ["verification_type"], unique=False)
    op.create_index(op.f("ix_reproducibility_verification_results_verification_status"), "reproducibility_verification_results", ["verification_status"], unique=False)
    op.create_index(op.f("ix_reproducibility_verification_results_immutable_hash"), "reproducibility_verification_results", ["immutable_hash"], unique=True)

    op.create_table(
        "artifact_replay_verifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("artifact_verification_id", sa.String(length=64), nullable=False),
        sa.Column("replay_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_status", sa.String(length=32), nullable=False),
        sa.Column("deterministic_summary", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_verification_id"], ["artifact_verification_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifact_replay_verifications_client_id"), "artifact_replay_verifications", ["client_id"], unique=False)
    op.create_index(op.f("ix_artifact_replay_verifications_artifact_verification_id"), "artifact_replay_verifications", ["artifact_verification_id"], unique=False)
    op.create_index(op.f("ix_artifact_replay_verifications_replay_hash"), "artifact_replay_verifications", ["replay_hash"], unique=False)
    op.create_index(op.f("ix_artifact_replay_verifications_replay_status"), "artifact_replay_verifications", ["replay_status"], unique=False)
    op.create_index(op.f("ix_artifact_replay_verifications_immutable_hash"), "artifact_replay_verifications", ["immutable_hash"], unique=True)

    op.create_table(
        "reproducible_build_receipts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("build_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_manifest_id"], ["reproducible_build_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reproducible_build_receipts_client_id"), "reproducible_build_receipts", ["client_id"], unique=False)
    op.create_index(op.f("ix_reproducible_build_receipts_build_manifest_id"), "reproducible_build_receipts", ["build_manifest_id"], unique=False)
    op.create_index(op.f("ix_reproducible_build_receipts_receipt_type"), "reproducible_build_receipts", ["receipt_type"], unique=False)
    op.create_index(op.f("ix_reproducible_build_receipts_payload_hash"), "reproducible_build_receipts", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_reproducible_build_receipts_immutable_hash"), "reproducible_build_receipts", ["immutable_hash"], unique=True)

    op.create_table(
        "reproducible_build_metadata_governance",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("build_manifest_id", sa.String(length=64), nullable=False),
        sa.Column("metadata_payload", json_type, nullable=False),
        sa.Column("metadata_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["build_manifest_id"], ["reproducible_build_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reproducible_build_metadata_governance_client_id"), "reproducible_build_metadata_governance", ["client_id"], unique=False)
    op.create_index(op.f("ix_reproducible_build_metadata_governance_build_manifest_id"), "reproducible_build_metadata_governance", ["build_manifest_id"], unique=False)
    op.create_index(op.f("ix_reproducible_build_metadata_governance_metadata_hash"), "reproducible_build_metadata_governance", ["metadata_hash"], unique=False)
    op.create_index(op.f("ix_reproducible_build_metadata_governance_immutable_hash"), "reproducible_build_metadata_governance", ["immutable_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("reproducible_build_metadata_governance")
    op.drop_table("reproducible_build_receipts")
    op.drop_table("artifact_replay_verifications")
    op.drop_table("reproducibility_verification_results")
    op.drop_table("build_environment_constraints")
    op.drop_table("source_artifact_lineage")
    op.drop_table("artifact_verification_records")
    op.drop_table("reproducible_build_manifests")
