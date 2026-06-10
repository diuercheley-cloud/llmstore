"""commercial report delivery logs

Revision ID: 20260514_0035
Revises: 20260514_0034
Create Date: 2026-05-14 14:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260514_0035"
down_revision = "20260514_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_report_delivery_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=True),
        sa.Column("report_format", sa.String(length=20), nullable=False),
        sa.Column("recipients_json", sa.JSON(), nullable=True),
        sa.Column("delivery_mode", sa.String(length=20), nullable=False),
        sa.Column("delivery_status", sa.String(length=20), nullable=False),
        sa.Column("smtp_host", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("attachment_names_json", sa.JSON(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_report_delivery_logs_schedule_id",
        "commercial_report_delivery_logs",
        ["schedule_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_report_delivery_logs_delivery_status",
        "commercial_report_delivery_logs",
        ["delivery_status"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_report_delivery_logs_created_at",
        "commercial_report_delivery_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commercial_report_delivery_logs_created_at", table_name="commercial_report_delivery_logs")
    op.drop_index("ix_commercial_report_delivery_logs_delivery_status", table_name="commercial_report_delivery_logs")
    op.drop_index("ix_commercial_report_delivery_logs_schedule_id", table_name="commercial_report_delivery_logs")
    op.drop_table("commercial_report_delivery_logs")
