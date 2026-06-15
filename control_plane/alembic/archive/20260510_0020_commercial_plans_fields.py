"""commercial plans fields

Revision ID: 20260510_0020
Revises: 18c9b4380f1f
Create Date: 2026-05-10 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260510_0020"
down_revision = "18c9b4380f1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "billing_plans",
        sa.Column("max_context_tokens", sa.Integer(), server_default="4096", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("requests_per_day", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("requests_per_month", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("rag_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("responses_enabled", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("tools_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("export_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column(
            "support_level", sa.String(length=64), server_default="Community", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("billing_plans", "support_level")
    op.drop_column("billing_plans", "export_enabled")
    op.drop_column("billing_plans", "tools_enabled")
    op.drop_column("billing_plans", "responses_enabled")
    op.drop_column("billing_plans", "rag_enabled")
    op.drop_column("billing_plans", "requests_per_month")
    op.drop_column("billing_plans", "requests_per_day")
    op.drop_column("billing_plans", "max_context_tokens")
