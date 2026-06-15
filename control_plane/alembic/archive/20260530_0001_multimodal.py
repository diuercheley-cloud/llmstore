"""Add multimodal support models

Revision ID: 20260530_0001
Revises: 20260529_0097
Create Date: 2026-05-30 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260530_0001"
down_revision: str | None = "20260529_0097"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("multimodal_assets"):
        op.create_table(
            "multimodal_assets",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "client_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("clients.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("asset_type", sa.String(length=32), nullable=False),
            sa.Column("storage_path", sa.String(length=256), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False),
            sa.Column("mime_type", sa.String(length=64), nullable=False),
            sa.Column("file_hash", sa.String(length=64), nullable=False),
            sa.Column("provenance", sa.String(length=256), nullable=True),
            sa.Column(
                "exif_sanitized", sa.Boolean(), nullable=False, server_default=sa.text("false")
            ),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    existing_indexes = (
        {index["name"] for index in inspector.get_indexes("multimodal_assets")}
        if inspector.has_table("multimodal_assets")
        else set()
    )
    if "ix_multimodal_assets_file_hash" not in existing_indexes:
        op.create_index("ix_multimodal_assets_file_hash", "multimodal_assets", ["file_hash"])
    if "ix_multimodal_assets_client_id" not in existing_indexes:
        op.create_index("ix_multimodal_assets_client_id", "multimodal_assets", ["client_id"])

    if not inspector.has_table("multimodal_requests"):
        op.create_table(
            "multimodal_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "client_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("clients.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("request_type", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "input_asset_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("multimodal_assets.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "output_asset_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("multimodal_assets.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("multimodal_requests"):
        op.drop_table("multimodal_requests")
    if inspector.has_table("multimodal_assets"):
        op.drop_table("multimodal_assets")
