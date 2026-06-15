"""Add Phase 74 Adapter Registry models

Revision ID: e68f9a82dc48
Revises: phase73_adapter_sandbox
Create Date: 2026-05-15 21:25:20.883747
"""

import sqlalchemy as sa
from alembic import op

revision = "e68f9a82dc48"
down_revision = "phase73_adapter_sandbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # signed_adapter_registry_entries
    op.create_table(
        "signed_adapter_registry_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("adapter_name", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("adapter_type", sa.String(length=50), nullable=False),
        sa.Column("manifest_id", sa.UUID(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("registry_status", sa.String(length=50), nullable=False),
        sa.Column("registry_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("signer_ref", sa.String(length=100), nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=500), nullable=True),
        sa.Column("blocked_reason", sa.String(length=500), nullable=True),
        sa.Column("deterministic_version", sa.String(length=50), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manifest_id"], ["adapter_manifests.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_signed_adapter_registry_entries_client_id"),
        "signed_adapter_registry_entries",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signed_adapter_registry_entries_adapter_name"),
        "signed_adapter_registry_entries",
        ["adapter_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signed_adapter_registry_entries_registry_status"),
        "signed_adapter_registry_entries",
        ["registry_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signed_adapter_registry_entries_manifest_hash"),
        "signed_adapter_registry_entries",
        ["manifest_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signed_adapter_registry_entries_registry_hash"),
        "signed_adapter_registry_entries",
        ["registry_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signed_adapter_registry_entries_immutable_hash"),
        "signed_adapter_registry_entries",
        ["immutable_hash"],
        unique=True,
    )

    # adapter_registry_policies
    op.create_table(
        "adapter_registry_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("policy_name", sa.String(length=100), nullable=False),
        sa.Column("allowed_adapter_types_json", sa.JSON(), nullable=False),
        sa.Column("denied_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("require_sandbox", sa.Boolean(), nullable=False),
        sa.Column("require_dry_run_default", sa.Boolean(), nullable=False),
        sa.Column("require_approval", sa.Boolean(), nullable=False),
        sa.Column("allow_offline_only", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_adapter_registry_policies_client_id"),
        "adapter_registry_policies",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_policies_immutable_hash"),
        "adapter_registry_policies",
        ["immutable_hash"],
        unique=True,
    )

    # adapter_registry_decisions
    op.create_table(
        "adapter_registry_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("registry_entry_id", sa.UUID(), nullable=False),
        sa.Column("decision_type", sa.String(length=50), nullable=False),
        sa.Column("decision_status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("decided_by", sa.String(length=100), nullable=False),
        sa.Column("advisory_only", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["registry_entry_id"], ["signed_adapter_registry_entries.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        op.f("ix_adapter_registry_decisions_client_id"),
        "adapter_registry_decisions",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_decisions_registry_entry_id"),
        "adapter_registry_decisions",
        ["registry_entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_decisions_immutable_hash"),
        "adapter_registry_decisions",
        ["immutable_hash"],
        unique=True,
    )

    # adapter_registry_receipts
    op.create_table(
        "adapter_registry_receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("registry_entry_id", sa.UUID(), nullable=False),
        sa.Column("receipt_type", sa.String(length=100), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["registry_entry_id"], ["signed_adapter_registry_entries.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        op.f("ix_adapter_registry_receipts_client_id"),
        "adapter_registry_receipts",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_receipts_registry_entry_id"),
        "adapter_registry_receipts",
        ["registry_entry_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_receipts_immutable_hash"),
        "adapter_registry_receipts",
        ["immutable_hash"],
        unique=True,
    )

    # adapter_registry_blocklist_entries
    op.create_table(
        "adapter_registry_blocklist_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("adapter_name", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_adapter_registry_blocklist_entries_client_id"),
        "adapter_registry_blocklist_entries",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_blocklist_entries_adapter_name"),
        "adapter_registry_blocklist_entries",
        ["adapter_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_blocklist_entries_manifest_hash"),
        "adapter_registry_blocklist_entries",
        ["manifest_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_blocklist_entries_immutable_hash"),
        "adapter_registry_blocklist_entries",
        ["immutable_hash"],
        unique=True,
    )

    # adapter_registry_allowlist_entries
    op.create_table(
        "adapter_registry_allowlist_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("adapter_name", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=50), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_adapter_registry_allowlist_entries_client_id"),
        "adapter_registry_allowlist_entries",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_allowlist_entries_adapter_name"),
        "adapter_registry_allowlist_entries",
        ["adapter_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_allowlist_entries_manifest_hash"),
        "adapter_registry_allowlist_entries",
        ["manifest_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_adapter_registry_allowlist_entries_immutable_hash"),
        "adapter_registry_allowlist_entries",
        ["immutable_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("adapter_registry_allowlist_entries")
    op.drop_table("adapter_registry_blocklist_entries")
    op.drop_table("adapter_registry_receipts")
    op.drop_table("adapter_registry_decisions")
    op.drop_table("adapter_registry_policies")
    op.drop_table("signed_adapter_registry_entries")
