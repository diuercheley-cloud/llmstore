"""billing invoices, customer payments, and client billing status"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260430_0004"
down_revision = "20260429_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("billing_status", sa.String(length=16), nullable=False, server_default="active"))
    op.create_index("ix_clients_billing_status", "clients", ["billing_status"])

    op.create_table(
        "billing_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("billing_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_plans.id"), nullable=True),
        sa.Column("pricing_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pricing_rules.id"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("monthly_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("included_tokens", sa.Integer(), nullable=False),
        sa.Column("used_tokens", sa.Integer(), nullable=False),
        sa.Column("overage_tokens", sa.Integer(), nullable=False),
        sa.Column("overage_price_per_1k_tokens", sa.Numeric(12, 6), nullable=False),
        sa.Column("overage_cost", sa.Numeric(12, 6), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 6), nullable=False),
        sa.Column("payment_method", sa.String(length=32), nullable=False, server_default="manual_pix"),
        sa.Column("payment_instructions", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", "period_start", "period_end", name="uq_billing_invoice_period"),
    )
    op.create_index("ix_billing_invoices_client_id", "billing_invoices", ["client_id"])
    op.create_index("ix_billing_invoices_billing_plan_id", "billing_invoices", ["billing_plan_id"])
    op.create_index("ix_billing_invoices_pricing_rule_id", "billing_invoices", ["pricing_rule_id"])
    op.create_index("ix_billing_invoices_status", "billing_invoices", ["status"])

    op.create_table(
        "customer_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 6), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("payment_method", sa.String(length=32), nullable=False, server_default="manual_pix"),
        sa.Column("payment_reference", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customer_payments_invoice_id", "customer_payments", ["invoice_id"])
    op.create_index("ix_customer_payments_client_id", "customer_payments", ["client_id"])
    op.create_index("ix_customer_payments_status", "customer_payments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_customer_payments_status", table_name="customer_payments")
    op.drop_index("ix_customer_payments_client_id", table_name="customer_payments")
    op.drop_index("ix_customer_payments_invoice_id", table_name="customer_payments")
    op.drop_table("customer_payments")

    op.drop_index("ix_billing_invoices_status", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_pricing_rule_id", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_billing_plan_id", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_client_id", table_name="billing_invoices")
    op.drop_table("billing_invoices")

    op.drop_index("ix_clients_billing_status", table_name="clients")
    op.drop_column("clients", "billing_status")
