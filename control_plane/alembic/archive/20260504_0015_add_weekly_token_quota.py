"""add_weekly_token_quota

Revision ID: 20260504_0015
Revises: 20260504_0014
Create Date: 2026-05-04 17:15:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260504_0015"
down_revision = "20260504_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_plans",
        sa.Column("weekly_token_quota", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "clients",
        sa.Column("weekly_token_quota", sa.Integer(), nullable=False, server_default="100000"),
    )


def downgrade():
    op.drop_column("clients", "weekly_token_quota")
    op.drop_column("billing_plans", "weekly_token_quota")
