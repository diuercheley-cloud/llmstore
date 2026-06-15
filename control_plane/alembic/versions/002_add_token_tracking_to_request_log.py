"""add token tracking to request log

Revision ID: 002_token_tracking
Revises: 001_initial
Create Date: 2026-06-11 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "002_token_tracking"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs", sa.Column("token_count_method", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "request_logs",
        sa.Column("tokens_estimated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "tokens_estimated")
    op.drop_column("request_logs", "token_count_method")
