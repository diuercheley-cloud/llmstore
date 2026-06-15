"""tts hardening

Revision ID: 20260509_0019
Revises: 20260506_0018
Create Date: 2026-05-09 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260509_0019"
down_revision = "20260506_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add TTS fields to billing_plans
    op.add_column(
        "billing_plans",
        sa.Column("tts_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("tts_chars_per_request", sa.Integer(), server_default="500", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("tts_chars_per_day", sa.Integer(), server_default="5000", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("tts_chars_per_month", sa.Integer(), server_default="50000", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("tts_audio_retention_days", sa.Integer(), server_default="7", nullable=False),
    )
    op.add_column(
        "billing_plans",
        sa.Column("tts_max_files", sa.Integer(), server_default="100", nullable=False),
    )

    # Add used_tts_chars to quota_counters
    op.add_column(
        "quota_counters",
        sa.Column("used_tts_chars", sa.Integer(), server_default="0", nullable=False),
    )

    # Create tts_usage_events table
    op.create_table(
        "tts_usage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("api_key_prefix", sa.String(length=16), nullable=True),
        sa.Column("chars_input", sa.Integer(), server_default="0", nullable=False),
        sa.Column("audio_file_id", sa.String(length=100), nullable=True),
        sa.Column("audio_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("plan_code", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tts_usage_events_client_id"), "tts_usage_events", ["client_id"], unique=False
    )
    op.create_index(
        op.f("ix_tts_usage_events_created_at"), "tts_usage_events", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tts_usage_events_created_at"), table_name="tts_usage_events")
    op.drop_index(op.f("ix_tts_usage_events_client_id"), table_name="tts_usage_events")
    op.drop_table("tts_usage_events")
    op.drop_column("quota_counters", "used_tts_chars")
    op.drop_column("billing_plans", "tts_max_files")
    op.drop_column("billing_plans", "tts_audio_retention_days")
    op.drop_column("billing_plans", "tts_chars_per_month")
    op.drop_column("billing_plans", "tts_chars_per_day")
    op.drop_column("billing_plans", "tts_chars_per_request")
    op.drop_column("billing_plans", "tts_enabled")
