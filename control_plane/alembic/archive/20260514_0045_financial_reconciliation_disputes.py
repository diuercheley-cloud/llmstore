"""financial_reconciliation_disputes

Revision ID: 20260514_0045
Revises: 20260514_0044
Create Date: 2026-05-14 21:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260514_0045"
down_revision = "20260514_0044"
branch_labels = None
depends_on = None


def upgrade():
    # commercial_financial_reconciliations
    op.create_table(
        "commercial_financial_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reconciliation_type", sa.String(length=32), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_amount_brl", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("actual_amount_brl", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("delta_amount_brl", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("discrepancy_percent", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_financial_reconciliations_reconciliation_type"),
        "commercial_financial_reconciliations",
        ["reconciliation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_reconciliations_client_id"),
        "commercial_financial_reconciliations",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_reconciliations_period_start"),
        "commercial_financial_reconciliations",
        ["period_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_reconciliations_period_end"),
        "commercial_financial_reconciliations",
        ["period_end"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_reconciliations_status"),
        "commercial_financial_reconciliations",
        ["status"],
        unique=False,
    )

    # commercial_billing_disputes
    op.create_table(
        "commercial_billing_disputes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qos_billing_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("wallet_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dispute_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("claimed_amount_brl", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("disputed_reason", sa.Text(), nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("credit_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["qos_billing_record_id"],
            ["commercial_qos_billing_records.id"],
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["billing_invoices.id"],
        ),
        sa.ForeignKeyConstraint(
            ["wallet_transaction_id"],
            ["ai_wallet_transactions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["credit_transaction_id"],
            ["ai_wallet_transactions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_billing_disputes_client_id"),
        "commercial_billing_disputes",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_billing_disputes_dispute_type"),
        "commercial_billing_disputes",
        ["dispute_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_billing_disputes_status"),
        "commercial_billing_disputes",
        ["status"],
        unique=False,
    )

    # commercial_financial_audit_events
    op.create_table(
        "commercial_financial_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_record_type", sa.String(length=64), nullable=True),
        sa.Column("related_record_id", sa.String(length=128), nullable=True),
        sa.Column("amount_brl", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_commercial_financial_audit_events_event_type"),
        "commercial_financial_audit_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_audit_events_client_id"),
        "commercial_financial_audit_events",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_audit_events_immutable_hash"),
        "commercial_financial_audit_events",
        ["immutable_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_financial_audit_events_created_at"),
        "commercial_financial_audit_events",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_table("commercial_financial_audit_events")
    op.drop_table("commercial_billing_disputes")
    op.drop_table("commercial_financial_reconciliations")
