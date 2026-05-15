"""enterprise_audit_portal

Revision ID: 20260514_0050
Revises: 20260514_0049
Create Date: 2026-05-14 23:59:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0050"
down_revision = "20260514_0049"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("commercial_evidence_packages", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("commercial_approval_chains", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("commercial_control_attestations", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("commercial_control_exceptions", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_foreign_key(None, "commercial_evidence_packages", "clients", ["client_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(None, "commercial_approval_chains", "clients", ["client_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(None, "commercial_control_attestations", "clients", ["client_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(None, "commercial_control_exceptions", "clients", ["client_id"], ["id"], ondelete="CASCADE")

    op.create_index(op.f("ix_commercial_evidence_packages_client_id"), "commercial_evidence_packages", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_approval_chains_client_id"), "commercial_approval_chains", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_control_attestations_client_id"), "commercial_control_attestations", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_control_exceptions_client_id"), "commercial_control_exceptions", ["client_id"], unique=False)

    op.create_table(
        "commercial_portal_audit_access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("ip_masked", sa.String(length=64), nullable=True),
        sa.Column("user_agent_sanitized", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_portal_audit_access_logs_action"), "commercial_portal_audit_access_logs", ["action"], unique=False)
    op.create_index(op.f("ix_commercial_portal_audit_access_logs_actor_id"), "commercial_portal_audit_access_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_commercial_portal_audit_access_logs_client_id"), "commercial_portal_audit_access_logs", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_portal_audit_access_logs_created_at"), "commercial_portal_audit_access_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_commercial_portal_audit_access_logs_resource_id"), "commercial_portal_audit_access_logs", ["resource_id"], unique=False)
    op.create_index(op.f("ix_commercial_portal_audit_access_logs_resource_type"), "commercial_portal_audit_access_logs", ["resource_type"], unique=False)

    op.create_table(
        "commercial_portal_saved_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("generated_by", sa.String(length=255), nullable=True),
        sa.Column("storage_ref", sa.String(length=512), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commercial_portal_saved_reports_client_id"), "commercial_portal_saved_reports", ["client_id"], unique=False)
    op.create_index(op.f("ix_commercial_portal_saved_reports_created_at"), "commercial_portal_saved_reports", ["created_at"], unique=False)
    op.create_index(op.f("ix_commercial_portal_saved_reports_expires_at"), "commercial_portal_saved_reports", ["expires_at"], unique=False)
    op.create_index(op.f("ix_commercial_portal_saved_reports_immutable_hash"), "commercial_portal_saved_reports", ["immutable_hash"], unique=False)
    op.create_index(op.f("ix_commercial_portal_saved_reports_period_end"), "commercial_portal_saved_reports", ["period_end"], unique=False)
    op.create_index(op.f("ix_commercial_portal_saved_reports_period_start"), "commercial_portal_saved_reports", ["period_start"], unique=False)
    op.create_index(op.f("ix_commercial_portal_saved_reports_report_type"), "commercial_portal_saved_reports", ["report_type"], unique=False)


def downgrade():
    op.drop_table("commercial_portal_saved_reports")
    op.drop_table("commercial_portal_audit_access_logs")
    op.drop_index(op.f("ix_commercial_control_exceptions_client_id"), table_name="commercial_control_exceptions")
    op.drop_index(op.f("ix_commercial_control_attestations_client_id"), table_name="commercial_control_attestations")
    op.drop_index(op.f("ix_commercial_approval_chains_client_id"), table_name="commercial_approval_chains")
    op.drop_index(op.f("ix_commercial_evidence_packages_client_id"), table_name="commercial_evidence_packages")
    op.drop_column("commercial_control_exceptions", "client_id")
    op.drop_column("commercial_control_attestations", "client_id")
    op.drop_column("commercial_approval_chains", "client_id")
    op.drop_column("commercial_evidence_packages", "client_id")
