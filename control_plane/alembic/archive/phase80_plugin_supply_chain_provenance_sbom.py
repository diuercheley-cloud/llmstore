"""Add Phase 80 plugin supply-chain provenance and SBOM placeholders

Revision ID: phase80_plugin_sbom
Revises: phase79_plugin_abi
Create Date: 2026-05-16 15:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "phase80_plugin_sbom"
down_revision = "phase79_plugin_abi"
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
        "plugin_provenance_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("plugin_contract_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_name", sa.String(length=120), nullable=False),
        sa.Column("artifact_version", sa.String(length=32), nullable=False),
        sa.Column("provenance_scope", sa.String(length=32), nullable=False),
        sa.Column("provenance_status", sa.String(length=32), nullable=False),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["plugin_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_client_id"),
        "plugin_provenance_records",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_plugin_contract_id"),
        "plugin_provenance_records",
        ["plugin_contract_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_artifact_name"),
        "plugin_provenance_records",
        ["artifact_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_artifact_version"),
        "plugin_provenance_records",
        ["artifact_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_provenance_scope"),
        "plugin_provenance_records",
        ["provenance_scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_provenance_status"),
        "plugin_provenance_records",
        ["provenance_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_provenance_hash"),
        "plugin_provenance_records",
        ["provenance_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_plugin_provenance_records_immutable_hash"),
        "plugin_provenance_records",
        ["immutable_hash"],
        unique=True,
    )

    op.create_table(
        "plugin_sbom_placeholders",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("provenance_record_id", sa.String(length=64), nullable=False),
        sa.Column("sbom_format", sa.String(length=64), nullable=False),
        sa.Column("dependency_summary_json", json_type, nullable=False),
        sa.Column("denied_dependencies_json", json_type, nullable=False),
        sa.Column("reproducible_build", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("offline_verifiable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sbom_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provenance_record_id"], ["plugin_provenance_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_sbom_placeholders_client_id"),
        "plugin_sbom_placeholders",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_sbom_placeholders_provenance_record_id"),
        "plugin_sbom_placeholders",
        ["provenance_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_sbom_placeholders_sbom_format"),
        "plugin_sbom_placeholders",
        ["sbom_format"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_sbom_placeholders_sbom_hash"),
        "plugin_sbom_placeholders",
        ["sbom_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_plugin_sbom_placeholders_immutable_hash"),
        "plugin_sbom_placeholders",
        ["immutable_hash"],
        unique=True,
    )

    op.create_table(
        "plugin_artifact_lineage",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("provenance_record_id", sa.String(length=64), nullable=False),
        sa.Column("parent_artifact_hash", sa.String(length=64), nullable=True),
        sa.Column("lineage_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provenance_record_id"], ["plugin_provenance_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_artifact_lineage_client_id"),
        "plugin_artifact_lineage",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_artifact_lineage_provenance_record_id"),
        "plugin_artifact_lineage",
        ["provenance_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_artifact_lineage_parent_artifact_hash"),
        "plugin_artifact_lineage",
        ["parent_artifact_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_artifact_lineage_lineage_hash"),
        "plugin_artifact_lineage",
        ["lineage_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_plugin_artifact_lineage_immutable_hash"),
        "plugin_artifact_lineage",
        ["immutable_hash"],
        unique=True,
    )

    op.create_table(
        "dependency_governance_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("policy_name", sa.String(length=120), nullable=False),
        sa.Column("denied_dependency_classes_json", json_type, nullable=False),
        sa.Column("allowed_dependency_classes_json", json_type, nullable=False),
        sa.Column(
            "require_reproducible_builds", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "require_offline_verification", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "require_placeholder_signature", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_dependency_governance_policies_client_id"),
        "dependency_governance_policies",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dependency_governance_policies_policy_name"),
        "dependency_governance_policies",
        ["policy_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_dependency_governance_policies_immutable_hash"),
        "dependency_governance_policies",
        ["immutable_hash"],
        unique=True,
    )

    op.create_table(
        "plugin_dependency_verifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("provenance_record_id", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("dependency_summary", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provenance_record_id"], ["plugin_provenance_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_dependency_verifications_client_id"),
        "plugin_dependency_verifications",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_dependency_verifications_provenance_record_id"),
        "plugin_dependency_verifications",
        ["provenance_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_dependency_verifications_verification_status"),
        "plugin_dependency_verifications",
        ["verification_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_dependency_verifications_immutable_hash"),
        "plugin_dependency_verifications",
        ["immutable_hash"],
        unique=True,
    )

    op.create_table(
        "plugin_signed_artifact_placeholders",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("provenance_record_id", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("signature_scope", sa.String(length=64), nullable=False),
        sa.Column("signature_status", sa.String(length=32), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provenance_record_id"], ["plugin_provenance_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_signed_artifact_placeholders_client_id"),
        "plugin_signed_artifact_placeholders",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_signed_artifact_placeholders_provenance_record_id"),
        "plugin_signed_artifact_placeholders",
        ["provenance_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_signed_artifact_placeholders_signature_scope"),
        "plugin_signed_artifact_placeholders",
        ["signature_scope"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_signed_artifact_placeholders_signature_status"),
        "plugin_signed_artifact_placeholders",
        ["signature_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_signed_artifact_placeholders_immutable_hash"),
        "plugin_signed_artifact_placeholders",
        ["immutable_hash"],
        unique=True,
    )

    op.create_table(
        "plugin_supply_chain_receipts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", uuid_type, nullable=False),
        sa.Column("provenance_record_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provenance_record_id"], ["plugin_provenance_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plugin_supply_chain_receipts_client_id"),
        "plugin_supply_chain_receipts",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_supply_chain_receipts_provenance_record_id"),
        "plugin_supply_chain_receipts",
        ["provenance_record_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_supply_chain_receipts_receipt_type"),
        "plugin_supply_chain_receipts",
        ["receipt_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_supply_chain_receipts_payload_hash"),
        "plugin_supply_chain_receipts",
        ["payload_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_plugin_supply_chain_receipts_immutable_hash"),
        "plugin_supply_chain_receipts",
        ["immutable_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("plugin_supply_chain_receipts")
    op.drop_table("plugin_signed_artifact_placeholders")
    op.drop_table("plugin_dependency_verifications")
    op.drop_table("dependency_governance_policies")
    op.drop_table("plugin_artifact_lineage")
    op.drop_table("plugin_sbom_placeholders")
    op.drop_table("plugin_provenance_records")
