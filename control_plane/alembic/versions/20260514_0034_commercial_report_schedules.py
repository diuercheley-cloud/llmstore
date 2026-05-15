"""commercial report schedules

Revision ID: 20260514_0034
Revises: 20260514_0033
Create Date: 2026-05-14 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0034"
down_revision = "20260514_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commercial_report_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("frequency", sa.String(length=20), nullable=False, server_default="monthly"),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("hour_utc", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("recipients_json", sa.JSON(), nullable=True),
        sa.Column("format", sa.String(length=20), nullable=False, server_default="html"),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_by", sa.String(length=120), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_report_schedules_enabled",
        "commercial_report_schedules",
        ["enabled"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_report_schedules_next_run_at",
        "commercial_report_schedules",
        ["next_run_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commercial_report_schedules_next_run_at", table_name="commercial_report_schedules")
    op.drop_index("ix_commercial_report_schedules_enabled", table_name="commercial_report_schedules")
    op.drop_table("commercial_report_schedules")
