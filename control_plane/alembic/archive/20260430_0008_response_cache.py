"""response cache and request log cache telemetry"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260430_0008"
down_revision = "20260430_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "response_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("cache_type", sa.String(length=16), nullable=False, server_default="exact"),
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=280), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("prompt_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cache_type", "endpoint", "model", "request_hash", name="uq_response_cache_lookup"),
    )
    op.create_index("ix_response_cache_endpoint", "response_cache", ["endpoint"])
    op.create_index("ix_response_cache_model", "response_cache", ["model"])
    op.create_index("ix_response_cache_request_hash", "response_cache", ["request_hash"])
    op.create_index("ix_response_cache_expires_at", "response_cache", ["expires_at"])

    op.add_column("request_logs", sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("request_logs", "cache_hit")
    op.drop_index("ix_response_cache_expires_at", table_name="response_cache")
    op.drop_index("ix_response_cache_request_hash", table_name="response_cache")
    op.drop_index("ix_response_cache_model", table_name="response_cache")
    op.drop_index("ix_response_cache_endpoint", table_name="response_cache")
    op.drop_table("response_cache")
