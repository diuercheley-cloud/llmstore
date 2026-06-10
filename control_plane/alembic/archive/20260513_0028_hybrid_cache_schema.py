"""align hybrid cache schema with response and semantic cache models

Revision ID: 20260513_0028
Revises: 20260513_0027
Create Date: 2026-05-13 12:58:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260513_0028"
down_revision = "20260513_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("response_cache", "endpoint", new_column_name="endpoint_type")

    op.add_column("response_cache", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("response_cache", sa.Column("provider", sa.String(length=64), nullable=True))
    op.add_column("response_cache", sa.Column("normalized_prompt_hash", sa.String(length=64), nullable=True))
    op.add_column("response_cache", sa.Column("prompt_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("response_cache", sa.Column("semantic_embedding_id", sa.String(length=64), nullable=True))
    op.add_column("response_cache", sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"))
    op.add_column("response_cache", sa.Column("metadata_json", sa.Text(), nullable=True))

    op.create_foreign_key(
        "fk_response_cache_client_id_clients",
        "response_cache",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("uq_response_cache_lookup", "response_cache", type_="unique")
    op.create_unique_constraint(
        "uq_response_cache_lookup",
        "response_cache",
        ["client_id", "cache_type", "endpoint_type", "model", "request_hash"],
    )

    op.drop_index("ix_response_cache_endpoint", table_name="response_cache")
    op.create_index("ix_response_cache_client_id", "response_cache", ["client_id"], unique=False)
    op.create_index("ix_response_cache_endpoint_type", "response_cache", ["endpoint_type"], unique=False)
    op.create_index("ix_response_cache_normalized_prompt_hash", "response_cache", ["normalized_prompt_hash"], unique=False)
    op.create_index("ix_response_cache_prompt_fingerprint", "response_cache", ["prompt_fingerprint"], unique=False)
    op.create_index("ix_response_cache_semantic_embedding_id", "response_cache", ["semantic_embedding_id"], unique=False)

    op.create_table(
        "semantic_cache_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint_type", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("normalized_prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("semantic_embedding_id", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("prompt_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens_estimated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("threshold_used", sa.Float(), nullable=False, server_default="0.85"),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="86400"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "endpoint_type", "model", "semantic_embedding_id", name="uq_semantic_cache_lookup"),
    )
    op.create_index("ix_semantic_cache_entries_client_id", "semantic_cache_entries", ["client_id"], unique=False)
    op.create_index("ix_semantic_cache_entries_endpoint_type", "semantic_cache_entries", ["endpoint_type"], unique=False)
    op.create_index("ix_semantic_cache_entries_expires_at", "semantic_cache_entries", ["expires_at"], unique=False)
    op.create_index("ix_semantic_cache_entries_model", "semantic_cache_entries", ["model"], unique=False)
    op.create_index("ix_semantic_cache_entries_normalized_prompt_hash", "semantic_cache_entries", ["normalized_prompt_hash"], unique=False)
    op.create_index("ix_semantic_cache_entries_semantic_embedding_id", "semantic_cache_entries", ["semantic_embedding_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_semantic_cache_entries_semantic_embedding_id", table_name="semantic_cache_entries")
    op.drop_index("ix_semantic_cache_entries_normalized_prompt_hash", table_name="semantic_cache_entries")
    op.drop_index("ix_semantic_cache_entries_model", table_name="semantic_cache_entries")
    op.drop_index("ix_semantic_cache_entries_expires_at", table_name="semantic_cache_entries")
    op.drop_index("ix_semantic_cache_entries_endpoint_type", table_name="semantic_cache_entries")
    op.drop_index("ix_semantic_cache_entries_client_id", table_name="semantic_cache_entries")
    op.drop_table("semantic_cache_entries")

    op.drop_index("ix_response_cache_semantic_embedding_id", table_name="response_cache")
    op.drop_index("ix_response_cache_prompt_fingerprint", table_name="response_cache")
    op.drop_index("ix_response_cache_normalized_prompt_hash", table_name="response_cache")
    op.drop_index("ix_response_cache_endpoint_type", table_name="response_cache")
    op.drop_index("ix_response_cache_client_id", table_name="response_cache")
    op.create_index("ix_response_cache_endpoint", "response_cache", ["endpoint_type"], unique=False)

    op.drop_constraint("uq_response_cache_lookup", "response_cache", type_="unique")
    op.create_unique_constraint(
        "uq_response_cache_lookup",
        "response_cache",
        ["cache_type", "endpoint_type", "model", "request_hash"],
    )
    op.drop_constraint("fk_response_cache_client_id_clients", "response_cache", type_="foreignkey")

    op.drop_column("response_cache", "metadata_json")
    op.drop_column("response_cache", "ttl_seconds")
    op.drop_column("response_cache", "semantic_embedding_id")
    op.drop_column("response_cache", "prompt_fingerprint")
    op.drop_column("response_cache", "normalized_prompt_hash")
    op.drop_column("response_cache", "provider")
    op.drop_column("response_cache", "client_id")

    op.alter_column("response_cache", "endpoint_type", new_column_name="endpoint")
