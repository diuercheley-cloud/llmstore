"""pricing rules and request costs"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260429_0003"
down_revision = "20260429_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pricing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("billing_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_plans.id"), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("monthly_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("overage_price_per_1k_tokens", sa.Numeric(12, 6), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pricing_rules_billing_plan_id", "pricing_rules", ["billing_plan_id"])
    op.add_column("request_logs", sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("request_logs", "estimated_cost_usd")
    op.drop_index("ix_pricing_rules_billing_plan_id", table_name="pricing_rules")
    op.drop_table("pricing_rules")
