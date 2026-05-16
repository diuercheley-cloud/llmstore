"""Add Phase 78 compatibility contracts and version negotiation

Revision ID: phase78_compatibility_contracts
Revises: phase77_federation_sync_protocol
Create Date: 2026-05-16 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "phase78_compatibility_contracts"
down_revision = "phase77_federation_sync_protocol"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compatibility_contracts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("contract_name", sa.String(length=120), nullable=False),
        sa.Column("contract_scope", sa.String(length=64), nullable=False),
        sa.Column("semantic_version", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("compatibility_status", sa.String(length=32), nullable=False),
        sa.Column("deterministic_version", sa.String(length=32), nullable=False),
        sa.Column("contract_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compatibility_contracts_client_id"), "compatibility_contracts", ["client_id"], unique=False)
    op.create_index(op.f("ix_compatibility_contracts_contract_name"), "compatibility_contracts", ["contract_name"], unique=False)
    op.create_index(op.f("ix_compatibility_contracts_contract_scope"), "compatibility_contracts", ["contract_scope"], unique=False)
    op.create_index(op.f("ix_compatibility_contracts_semantic_version"), "compatibility_contracts", ["semantic_version"], unique=False)
    op.create_index(op.f("ix_compatibility_contracts_compatibility_status"), "compatibility_contracts", ["compatibility_status"], unique=False)
    op.create_index(op.f("ix_compatibility_contracts_contract_hash"), "compatibility_contracts", ["contract_hash"], unique=True)
    op.create_index(op.f("ix_compatibility_contracts_immutable_hash"), "compatibility_contracts", ["immutable_hash"], unique=True)

    op.create_table(
        "compatibility_matrices",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("source_version", sa.String(length=32), nullable=False),
        sa.Column("target_version", sa.String(length=32), nullable=False),
        sa.Column("compatibility_type", sa.String(length=32), nullable=False),
        sa.Column("compatibility_status", sa.String(length=32), nullable=False),
        sa.Column("upgrade_supported", sa.Boolean(), nullable=False),
        sa.Column("downgrade_supported", sa.Boolean(), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compatibility_matrices_client_id"), "compatibility_matrices", ["client_id"], unique=False)
    op.create_index(op.f("ix_compatibility_matrices_source_version"), "compatibility_matrices", ["source_version"], unique=False)
    op.create_index(op.f("ix_compatibility_matrices_target_version"), "compatibility_matrices", ["target_version"], unique=False)
    op.create_index(op.f("ix_compatibility_matrices_compatibility_type"), "compatibility_matrices", ["compatibility_type"], unique=False)
    op.create_index(op.f("ix_compatibility_matrices_compatibility_status"), "compatibility_matrices", ["compatibility_status"], unique=False)
    op.create_index(op.f("ix_compatibility_matrices_immutable_hash"), "compatibility_matrices", ["immutable_hash"], unique=True)

    op.create_table(
        "version_negotiation_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("source_environment", sa.String(length=120), nullable=False),
        sa.Column("target_environment", sa.String(length=120), nullable=False),
        sa.Column("source_version", sa.String(length=32), nullable=False),
        sa.Column("target_version", sa.String(length=32), nullable=False),
        sa.Column("negotiated_version", sa.String(length=32), nullable=True),
        sa.Column("negotiation_status", sa.String(length=32), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_version_negotiation_sessions_client_id"), "version_negotiation_sessions", ["client_id"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_source_environment"), "version_negotiation_sessions", ["source_environment"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_target_environment"), "version_negotiation_sessions", ["target_environment"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_source_version"), "version_negotiation_sessions", ["source_version"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_target_version"), "version_negotiation_sessions", ["target_version"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_negotiated_version"), "version_negotiation_sessions", ["negotiated_version"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_negotiation_status"), "version_negotiation_sessions", ["negotiation_status"], unique=False)
    op.create_index(op.f("ix_version_negotiation_sessions_immutable_hash"), "version_negotiation_sessions", ["immutable_hash"], unique=True)

    op.create_table(
        "capability_negotiations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("negotiation_session_id", sa.String(length=64), nullable=False),
        sa.Column("requested_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("approved_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("denied_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("negotiation_status", sa.String(length=32), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["negotiation_session_id"], ["version_negotiation_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_capability_negotiations_client_id"), "capability_negotiations", ["client_id"], unique=False)
    op.create_index(op.f("ix_capability_negotiations_negotiation_session_id"), "capability_negotiations", ["negotiation_session_id"], unique=False)
    op.create_index(op.f("ix_capability_negotiations_negotiation_status"), "capability_negotiations", ["negotiation_status"], unique=False)
    op.create_index(op.f("ix_capability_negotiations_immutable_hash"), "capability_negotiations", ["immutable_hash"], unique=True)

    op.create_table(
        "feature_compatibility_flags",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("feature_name", sa.String(length=120), nullable=False),
        sa.Column("feature_scope", sa.String(length=120), nullable=False),
        sa.Column("minimum_supported_version", sa.String(length=32), nullable=False),
        sa.Column("maximum_supported_version", sa.String(length=32), nullable=False),
        sa.Column("deprecated_after_version", sa.String(length=32), nullable=True),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feature_compatibility_flags_client_id"), "feature_compatibility_flags", ["client_id"], unique=False)
    op.create_index(op.f("ix_feature_compatibility_flags_feature_name"), "feature_compatibility_flags", ["feature_name"], unique=False)
    op.create_index(op.f("ix_feature_compatibility_flags_feature_scope"), "feature_compatibility_flags", ["feature_scope"], unique=False)
    op.create_index(op.f("ix_feature_compatibility_flags_immutable_hash"), "feature_compatibility_flags", ["immutable_hash"], unique=True)

    op.create_table(
        "deprecation_lifecycles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("contract_id", sa.String(length=64), nullable=False),
        sa.Column("deprecation_reason", sa.Text(), nullable=False),
        sa.Column("deprecation_status", sa.String(length=32), nullable=False),
        sa.Column("replacement_contract", sa.String(length=64), nullable=True),
        sa.Column("migration_required", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["compatibility_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deprecation_lifecycles_client_id"), "deprecation_lifecycles", ["client_id"], unique=False)
    op.create_index(op.f("ix_deprecation_lifecycles_contract_id"), "deprecation_lifecycles", ["contract_id"], unique=False)
    op.create_index(op.f("ix_deprecation_lifecycles_deprecation_status"), "deprecation_lifecycles", ["deprecation_status"], unique=False)
    op.create_index(op.f("ix_deprecation_lifecycles_immutable_hash"), "deprecation_lifecycles", ["immutable_hash"], unique=True)

    op.create_table(
        "compatibility_verification_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("contract_id", sa.String(length=64), nullable=False),
        sa.Column("verification_type", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("compatibility_summary", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["compatibility_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compatibility_verification_results_client_id"), "compatibility_verification_results", ["client_id"], unique=False)
    op.create_index(op.f("ix_compatibility_verification_results_contract_id"), "compatibility_verification_results", ["contract_id"], unique=False)
    op.create_index(op.f("ix_compatibility_verification_results_verification_type"), "compatibility_verification_results", ["verification_type"], unique=False)
    op.create_index(op.f("ix_compatibility_verification_results_verification_status"), "compatibility_verification_results", ["verification_status"], unique=False)
    op.create_index(op.f("ix_compatibility_verification_results_immutable_hash"), "compatibility_verification_results", ["immutable_hash"], unique=True)

    op.create_table(
        "compatibility_receipts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("contract_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["compatibility_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compatibility_receipts_client_id"), "compatibility_receipts", ["client_id"], unique=False)
    op.create_index(op.f("ix_compatibility_receipts_contract_id"), "compatibility_receipts", ["contract_id"], unique=False)
    op.create_index(op.f("ix_compatibility_receipts_receipt_type"), "compatibility_receipts", ["receipt_type"], unique=False)
    op.create_index(op.f("ix_compatibility_receipts_payload_hash"), "compatibility_receipts", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_compatibility_receipts_immutable_hash"), "compatibility_receipts", ["immutable_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("compatibility_receipts")
    op.drop_table("compatibility_verification_results")
    op.drop_table("deprecation_lifecycles")
    op.drop_table("feature_compatibility_flags")
    op.drop_table("capability_negotiations")
    op.drop_table("version_negotiation_sessions")
    op.drop_table("compatibility_matrices")
    op.drop_table("compatibility_contracts")
