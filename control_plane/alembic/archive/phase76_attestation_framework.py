"""Add Phase 76 sovereign execution attestation framework

Revision ID: phase76_attestation_framework
Revises: phase75_adapter_promotion
Create Date: 2026-05-16 10:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "phase76_attestation_framework"
down_revision = "phase75_adapter_promotion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sovereign_execution_attestations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("attestation_type", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=64), nullable=False),
        sa.Column("subject_ref", sa.String(length=255), nullable=False),
        sa.Column("attestation_scope", sa.String(length=255), nullable=False),
        sa.Column("attestation_status", sa.String(length=32), nullable=False),
        sa.Column("deterministic_version", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("attestation_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_attestation_hash", sa.String(length=64), nullable=True),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("attestation_chain_position", sa.String(length=32), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("offline_verifiable", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sovereign_execution_attestations_client_id"), "sovereign_execution_attestations", ["client_id"], unique=False)
    op.create_index(op.f("ix_sovereign_execution_attestations_attestation_type"), "sovereign_execution_attestations", ["attestation_type"], unique=False)
    op.create_index(op.f("ix_sovereign_execution_attestations_subject_type"), "sovereign_execution_attestations", ["subject_type"], unique=False)
    op.create_index(op.f("ix_sovereign_execution_attestations_subject_ref"), "sovereign_execution_attestations", ["subject_ref"], unique=False)
    op.create_index(op.f("ix_sovereign_execution_attestations_attestation_status"), "sovereign_execution_attestations", ["attestation_status"], unique=False)
    op.create_index(op.f("ix_sovereign_execution_attestations_payload_hash"), "sovereign_execution_attestations", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_sovereign_execution_attestations_attestation_hash"), "sovereign_execution_attestations", ["attestation_hash"], unique=True)
    op.create_index(op.f("ix_sovereign_execution_attestations_immutable_hash"), "sovereign_execution_attestations", ["immutable_hash"], unique=True)

    op.create_table(
        "attestation_trust_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("policy_name", sa.String(length=120), nullable=False),
        sa.Column("allowed_attestation_types_json", sa.JSON(), nullable=False),
        sa.Column("require_chain_integrity", sa.Boolean(), nullable=False),
        sa.Column("require_replay_verification", sa.Boolean(), nullable=False),
        sa.Column("require_offline_verification", sa.Boolean(), nullable=False),
        sa.Column("require_signature_placeholder", sa.Boolean(), nullable=False),
        sa.Column("federation_allowed", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attestation_trust_policies_client_id"), "attestation_trust_policies", ["client_id"], unique=False)
    op.create_index(op.f("ix_attestation_trust_policies_immutable_hash"), "attestation_trust_policies", ["immutable_hash"], unique=True)

    op.create_table(
        "attestation_federation_bundles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("bundle_name", sa.String(length=120), nullable=False),
        sa.Column("bundle_scope", sa.String(length=255), nullable=False),
        sa.Column("bundle_hash", sa.String(length=64), nullable=False),
        sa.Column("source_environment", sa.String(length=120), nullable=False),
        sa.Column("target_environment", sa.String(length=120), nullable=False),
        sa.Column("bundle_status", sa.String(length=32), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("offline_verifiable", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attestation_federation_bundles_client_id"), "attestation_federation_bundles", ["client_id"], unique=False)
    op.create_index(op.f("ix_attestation_federation_bundles_bundle_status"), "attestation_federation_bundles", ["bundle_status"], unique=False)
    op.create_index(op.f("ix_attestation_federation_bundles_bundle_hash"), "attestation_federation_bundles", ["bundle_hash"], unique=True)
    op.create_index(op.f("ix_attestation_federation_bundles_immutable_hash"), "attestation_federation_bundles", ["immutable_hash"], unique=True)

    op.create_table(
        "attestation_verification_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("attestation_id", sa.String(length=64), nullable=False),
        sa.Column("verification_type", sa.String(length=64), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("verification_summary", sa.Text(), nullable=False),
        sa.Column("replay_verified", sa.Boolean(), nullable=False),
        sa.Column("chain_verified", sa.Boolean(), nullable=False),
        sa.Column("offline_verified", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attestation_id"], ["sovereign_execution_attestations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attestation_verification_results_client_id"), "attestation_verification_results", ["client_id"], unique=False)
    op.create_index(op.f("ix_attestation_verification_results_attestation_id"), "attestation_verification_results", ["attestation_id"], unique=False)
    op.create_index(op.f("ix_attestation_verification_results_verification_status"), "attestation_verification_results", ["verification_status"], unique=False)
    op.create_index(op.f("ix_attestation_verification_results_immutable_hash"), "attestation_verification_results", ["immutable_hash"], unique=True)

    op.create_table(
        "attestation_receipts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("attestation_id", sa.String(length=64), nullable=False),
        sa.Column("receipt_type", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_placeholder", sa.String(length=255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attestation_id"], ["sovereign_execution_attestations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attestation_receipts_client_id"), "attestation_receipts", ["client_id"], unique=False)
    op.create_index(op.f("ix_attestation_receipts_attestation_id"), "attestation_receipts", ["attestation_id"], unique=False)
    op.create_index(op.f("ix_attestation_receipts_payload_hash"), "attestation_receipts", ["payload_hash"], unique=False)
    op.create_index(op.f("ix_attestation_receipts_immutable_hash"), "attestation_receipts", ["immutable_hash"], unique=True)

    op.create_table(
        "attestation_chain_links",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("attestation_id", sa.String(length=64), nullable=False),
        sa.Column("previous_link_hash", sa.String(length=64), nullable=True),
        sa.Column("current_link_hash", sa.String(length=64), nullable=False),
        sa.Column("chain_position", sa.String(length=32), nullable=False),
        sa.Column("replay_verifiable", sa.Boolean(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attestation_id"], ["sovereign_execution_attestations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attestation_chain_links_client_id"), "attestation_chain_links", ["client_id"], unique=False)
    op.create_index(op.f("ix_attestation_chain_links_attestation_id"), "attestation_chain_links", ["attestation_id"], unique=False)
    op.create_index(op.f("ix_attestation_chain_links_current_link_hash"), "attestation_chain_links", ["current_link_hash"], unique=True)
    op.create_index(op.f("ix_attestation_chain_links_immutable_hash"), "attestation_chain_links", ["immutable_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("attestation_chain_links")
    op.drop_table("attestation_receipts")
    op.drop_table("attestation_verification_results")
    op.drop_table("attestation_federation_bundles")
    op.drop_table("attestation_trust_policies")
    op.drop_table("sovereign_execution_attestations")
