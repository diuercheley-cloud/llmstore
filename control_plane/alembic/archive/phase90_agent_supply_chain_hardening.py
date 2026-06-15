# Models: AgentBundleSignature, AgentBundleProvenance, AgentBundleCompatibility, AgentPublisherProfile, AgentPublicationReview
"""Harden Marketplace and Supply Chain

Revision ID: phase90_agent_supply_chain
Revises: phase89_agentic_rbac_hardening
Create Date: 2026-05-22 19:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "phase90_agent_supply_chain"
down_revision: Union[str, None] = "phase89_agentic_rbac_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_bundle_signatures
    op.create_table(
        "agent_bundle_signatures",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signature_type", sa.String(length=32), nullable=False, server_default="ed25519"),
        sa.Column("signature_value", sa.Text(), nullable=False),
        sa.Column("public_key_id", sa.String(length=128), nullable=False),
        sa.Column("signed_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["agent_bundle_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_bundle_signatures_version_id"),
        "agent_bundle_signatures",
        ["version_id"],
        unique=False,
    )

    # 2. agent_bundle_provenance
    op.create_table(
        "agent_bundle_provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("build_id", sa.String(length=128), nullable=True),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("builder_id", sa.String(length=128), nullable=True),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["agent_bundle_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_bundle_provenance_version_id"),
        "agent_bundle_provenance",
        ["version_id"],
        unique=False,
    )

    # 3. agent_bundle_compatibility
    op.create_table(
        "agent_bundle_compatibility",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_version_min", sa.String(length=64), nullable=False),
        sa.Column("platform_version_max", sa.String(length=64), nullable=True),
        sa.Column("required_flags_json", sa.JSON(), nullable=False),
        sa.Column("conflicting_flags_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["agent_bundle_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_bundle_compatibility_version_id"),
        "agent_bundle_compatibility",
        ["version_id"],
        unique=False,
    )

    # 4. agent_publisher_profiles
    op.create_table(
        "agent_publisher_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=128), nullable=False),
        sa.Column("organization", sa.String(length=128), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 5. agent_publication_reviews
    op.create_table(
        "agent_publication_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("risk_assessment_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["agent_bundle_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_publication_reviews_version_id"),
        "agent_publication_reviews",
        ["version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("agent_publication_reviews")
    op.drop_table("agent_publisher_profiles")
    op.drop_table("agent_bundle_compatibility")
    op.drop_table("agent_bundle_provenance")
    op.drop_table("agent_bundle_signatures")
