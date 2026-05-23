"""Add Phase 79 formal plugin ABI and extension runtime

Revision ID: phase79_plugin_abi
Revises: phase78_compatibility_contracts
Create Date: 2026-05-16 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "phase79_plugin_abi"
down_revision = "phase78_compatibility_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_abi_contracts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("plugin_name", sa.String(length=120), nullable=False),
        sa.Column("plugin_version", sa.String(length=32), nullable=False),
        sa.Column("abi_version", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("contract_scope", sa.String(length=32), nullable=False),
        sa.Column("contract_status", sa.String(length=32), nullable=False),
        sa.Column("deterministic_version", sa.String(length=32), nullable=False),
        sa.Column("contract_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_abi_contracts_client_id"), "plugin_abi_contracts", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_abi_contracts_plugin_name"), "plugin_abi_contracts", ["plugin_name"], unique=False)
    op.create_index(op.f("ix_plugin_abi_contracts_plugin_version"), "plugin_abi_contracts", ["plugin_version"], unique=False)
    op.create_index(op.f("ix_plugin_abi_contracts_abi_version"), "plugin_abi_contracts", ["abi_version"], unique=False)
    op.create_index(op.f("ix_plugin_abi_contracts_contract_scope"), "plugin_abi_contracts", ["contract_scope"], unique=False)
    op.create_index(op.f("ix_plugin_abi_contracts_contract_status"), "plugin_abi_contracts", ["contract_status"], unique=False)
    op.create_index(op.f("ix_plugin_abi_contracts_contract_hash"), "plugin_abi_contracts", ["contract_hash"], unique=True)
    op.create_index(op.f("ix_plugin_abi_contracts_immutable_hash"), "plugin_abi_contracts", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_capability_boundaries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("allowed_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("denied_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("isolation_required", sa.Boolean(), nullable=False),
        sa.Column("offline_only", sa.Boolean(), nullable=False),
        sa.Column("network_allowed", sa.Boolean(), nullable=False),
        sa.Column("subprocess_allowed", sa.Boolean(), nullable=False),
        sa.Column("filesystem_write_allowed", sa.Boolean(), nullable=False),
        sa.Column("external_secret_access_allowed", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_capability_boundaries_client_id"), "plugin_capability_boundaries", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_capability_boundaries_abi_contract_id"), "plugin_capability_boundaries", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_plugin_capability_boundaries_immutable_hash"), "plugin_capability_boundaries", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_runtime_compatibility_checks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("runtime_version", sa.String(length=32), nullable=False),
        sa.Column("compatibility_status", sa.String(length=32), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("federation_safe", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_runtime_compatibility_checks_client_id"), "plugin_runtime_compatibility_checks", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_compatibility_checks_abi_contract_id"), "plugin_runtime_compatibility_checks", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_compatibility_checks_runtime_version"), "plugin_runtime_compatibility_checks", ["runtime_version"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_compatibility_checks_compatibility_status"), "plugin_runtime_compatibility_checks", ["compatibility_status"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_compatibility_checks_immutable_hash"), "plugin_runtime_compatibility_checks", ["immutable_hash"], unique=True)

    op.create_table(
        "deterministic_extension_load_plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("load_order", sa.Text(), nullable=False),
        sa.Column("load_plan_hash", sa.String(length=64), nullable=False),
        sa.Column("load_status", sa.String(length=32), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deterministic_extension_load_plans_client_id"), "deterministic_extension_load_plans", ["client_id"], unique=False)
    op.create_index(op.f("ix_deterministic_extension_load_plans_abi_contract_id"), "deterministic_extension_load_plans", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_deterministic_extension_load_plans_load_plan_hash"), "deterministic_extension_load_plans", ["load_plan_hash"], unique=True)
    op.create_index(op.f("ix_deterministic_extension_load_plans_load_status"), "deterministic_extension_load_plans", ["load_status"], unique=False)
    op.create_index(op.f("ix_deterministic_extension_load_plans_immutable_hash"), "deterministic_extension_load_plans", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_isolation_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("policy_name", sa.String(length=120), nullable=False),
        sa.Column("isolation_level", sa.String(length=32), nullable=False),
        sa.Column("deny_network", sa.Boolean(), nullable=False),
        sa.Column("deny_subprocess", sa.Boolean(), nullable=False),
        sa.Column("deny_dynamic_import", sa.Boolean(), nullable=False),
        sa.Column("deny_external_filesystem_write", sa.Boolean(), nullable=False),
        sa.Column("deny_plaintext_secret_access", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_isolation_policies_client_id"), "plugin_isolation_policies", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_isolation_policies_policy_name"), "plugin_isolation_policies", ["policy_name"], unique=False)
    op.create_index(op.f("ix_plugin_isolation_policies_isolation_level"), "plugin_isolation_policies", ["isolation_level"], unique=False)
    op.create_index(op.f("ix_plugin_isolation_policies_immutable_hash"), "plugin_isolation_policies", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_lifecycle_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_event_type", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_lifecycle_events_client_id"), "plugin_lifecycle_events", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_lifecycle_events_abi_contract_id"), "plugin_lifecycle_events", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_plugin_lifecycle_events_lifecycle_event_type"), "plugin_lifecycle_events", ["lifecycle_event_type"], unique=False)
    op.create_index(op.f("ix_plugin_lifecycle_events_lifecycle_status"), "plugin_lifecycle_events", ["lifecycle_status"], unique=False)
    op.create_index(op.f("ix_plugin_lifecycle_events_immutable_hash"), "plugin_lifecycle_events", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_replay_verification_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("replay_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("deterministic_summary", sa.Text(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_replay_verification_results_client_id"), "plugin_replay_verification_results", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_replay_verification_results_abi_contract_id"), "plugin_replay_verification_results", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_plugin_replay_verification_results_verification_status"), "plugin_replay_verification_results", ["verification_status"], unique=False)
    op.create_index(op.f("ix_plugin_replay_verification_results_replay_hash"), "plugin_replay_verification_results", ["replay_hash"], unique=False)
    op.create_index(op.f("ix_plugin_replay_verification_results_immutable_hash"), "plugin_replay_verification_results", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_federation_compatibility",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("source_environment", sa.String(length=120), nullable=False),
        sa.Column("target_environment", sa.String(length=120), nullable=False),
        sa.Column("federation_status", sa.String(length=32), nullable=False),
        sa.Column("compatibility_hash", sa.String(length=64), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_federation_compatibility_client_id"), "plugin_federation_compatibility", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_federation_compatibility_abi_contract_id"), "plugin_federation_compatibility", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_plugin_federation_compatibility_source_environment"), "plugin_federation_compatibility", ["source_environment"], unique=False)
    op.create_index(op.f("ix_plugin_federation_compatibility_target_environment"), "plugin_federation_compatibility", ["target_environment"], unique=False)
    op.create_index(op.f("ix_plugin_federation_compatibility_federation_status"), "plugin_federation_compatibility", ["federation_status"], unique=False)
    op.create_index(op.f("ix_plugin_federation_compatibility_compatibility_hash"), "plugin_federation_compatibility", ["compatibility_hash"], unique=True)
    op.create_index(op.f("ix_plugin_federation_compatibility_immutable_hash"), "plugin_federation_compatibility", ["immutable_hash"], unique=True)

    op.create_table(
        "plugin_runtime_receipts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("abi_contract_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["abi_contract_id"], ["plugin_abi_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plugin_runtime_receipts_client_id"), "plugin_runtime_receipts", ["client_id"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_receipts_abi_contract_id"), "plugin_runtime_receipts", ["abi_contract_id"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_receipts_receipt_type"), "plugin_runtime_receipts", ["receipt_type"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_receipts_payload_hash"), "plugin_runtime_receipts", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_plugin_runtime_receipts_immutable_hash"), "plugin_runtime_receipts", ["immutable_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("plugin_runtime_receipts")
    op.drop_table("plugin_federation_compatibility")
    op.drop_table("plugin_replay_verification_results")
    op.drop_table("plugin_lifecycle_events")
    op.drop_table("plugin_isolation_policies")
    op.drop_table("deterministic_extension_load_plans")
    op.drop_table("plugin_runtime_compatibility_checks")
    op.drop_table("plugin_capability_boundaries")
    op.drop_table("plugin_abi_contracts")
