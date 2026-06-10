"""initial schema"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260429_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("daily_token_quota", sa.Integer(), nullable=False, server_default="20000"),
        sa.Column("monthly_token_quota", sa.Integer(), nullable=False, server_default="300000"),
        sa.Column("max_context_tokens", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False, server_default="2048"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_table(
        "request_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("is_stream", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_summary", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_request_logs_client_id", "request_logs", ["client_id"])
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", "period_start", "period_type", name="uq_usage_record_period"),
    )
    op.create_index("ix_usage_records_client_id", "usage_records", ["client_id"])
    op.create_index("ix_usage_records_period_start", "usage_records", ["period_start"])
    op.create_table(
        "model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="llama.cpp"),
        sa.Column("model_file", sa.String(length=255), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=False, server_default="4096"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="configured"),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "quota_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_id", "period_start", "period_type", name="uq_quota_counter_period"),
    )
    op.create_index("ix_quota_counters_client_id", "quota_counters", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_quota_counters_client_id", table_name="quota_counters")
    op.drop_table("quota_counters")
    op.drop_table("model_registry")
    op.drop_index("ix_usage_records_period_start", table_name="usage_records")
    op.drop_index("ix_usage_records_client_id", table_name="usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_request_logs_client_id", table_name="request_logs")
    op.drop_table("request_logs")
    op.drop_index("ix_api_keys_key_prefix", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_table("clients")
