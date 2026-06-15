"""operational_controls

Revision ID: 20260514_0051
Revises: 20260514_0050
Create Date: 2026-05-14 23:59:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260514_0051"
down_revision = "20260514_0050"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commercial_operational_controls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_email", sa.String(length=255), nullable=True),
        sa.Column("review_frequency", sa.String(length=16), nullable=False),
        sa.Column("effectiveness_score", sa.Integer(), nullable=True),
        sa.Column("effectiveness_status", sa.String(length=24), nullable=False),
        sa.Column("evidence_sla_days", sa.Integer(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("control_code"),
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_category"),
        "commercial_operational_controls",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_control_code"),
        "commercial_operational_controls",
        ["control_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_effectiveness_status"),
        "commercial_operational_controls",
        ["effectiveness_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_enabled"),
        "commercial_operational_controls",
        ["enabled"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_name"),
        "commercial_operational_controls",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_next_review_due_at"),
        "commercial_operational_controls",
        ["next_review_due_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_owner_email"),
        "commercial_operational_controls",
        ["owner_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_controls_owner_id"),
        "commercial_operational_controls",
        ["owner_id"],
        unique=False,
    )

    op.create_table(
        "commercial_operational_evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("freshness_status", sa.String(length=16), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["control_id"], ["commercial_operational_controls.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_operational_evidences_collected_at"),
        "commercial_operational_evidences",
        ["collected_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_evidences_control_id"),
        "commercial_operational_evidences",
        ["control_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_evidences_evidence_type"),
        "commercial_operational_evidences",
        ["evidence_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_evidences_expires_at"),
        "commercial_operational_evidences",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_evidences_freshness_status"),
        "commercial_operational_evidences",
        ["freshness_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_evidences_immutable_hash"),
        "commercial_operational_evidences",
        ["immutable_hash"],
        unique=False,
    )

    op.create_table(
        "commercial_operational_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_period_start", sa.Date(), nullable=False),
        sa.Column("review_period_end", sa.Date(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("evidence_package_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["control_id"], ["commercial_operational_controls.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["evidence_package_id"], ["commercial_evidence_packages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_operational_reviews_control_id"),
        "commercial_operational_reviews",
        ["control_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_reviews_evidence_package_id"),
        "commercial_operational_reviews",
        ["evidence_package_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_reviews_review_period_end"),
        "commercial_operational_reviews",
        ["review_period_end"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_reviews_review_period_start"),
        "commercial_operational_reviews",
        ["review_period_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_reviews_status"),
        "commercial_operational_reviews",
        ["status"],
        unique=False,
    )

    op.create_table(
        "commercial_operational_exception_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exception_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("linkage_reason", sa.Text(), nullable=True),
        sa.Column("remediation_status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["control_id"], ["commercial_operational_controls.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["exception_id"], ["commercial_control_exceptions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_operational_exception_links_control_id"),
        "commercial_operational_exception_links",
        ["control_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_exception_links_exception_id"),
        "commercial_operational_exception_links",
        ["exception_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_operational_exception_links_remediation_status"),
        "commercial_operational_exception_links",
        ["remediation_status"],
        unique=False,
    )


def downgrade():
    op.drop_table("commercial_operational_exception_links")
    op.drop_table("commercial_operational_reviews")
    op.drop_table("commercial_operational_evidences")
    op.drop_table("commercial_operational_controls")
