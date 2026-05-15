"""add sanitized tool call fields to request logs

Revision ID: 20260514_0029
Revises: 6aa96c5bcb12
Create Date: 2026-05-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0029"
down_revision = "6aa96c5bcb12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("request_logs", sa.Column("tool_call_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("request_logs", sa.Column("tool_calls_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_logs", "tool_calls_json")
    op.drop_column("request_logs", "tool_call_count")
