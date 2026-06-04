"""billing plans"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260429_0002"
down_revision = "20260429_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("daily_token_quota", sa.Integer(), nullable=False),
        sa.Column("monthly_token_quota", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("allow_streaming", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_billing_plans_code", "billing_plans", ["code"])
    op.add_column("clients", sa.Column("billing_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_clients_billing_plan_id", "clients", ["billing_plan_id"])
    op.create_foreign_key("fk_clients_billing_plan_id", "clients", "billing_plans", ["billing_plan_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_clients_billing_plan_id", "clients", type_="foreignkey")
    op.drop_index("ix_clients_billing_plan_id", table_name="clients")
    op.drop_column("clients", "billing_plan_id")
    op.drop_index("ix_billing_plans_code", table_name="billing_plans")
    op.drop_table("billing_plans")
