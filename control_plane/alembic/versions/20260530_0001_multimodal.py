"""Add multimodal support models

Revision ID: 20260530_0001
Revises: 20260529_0097
Create Date: 2026-05-30 08:00:00.000000

"""
from typing import Sequence, Optional

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0001'
down_revision: Optional[str] = '20260529_0097'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. Create multimodal_assets table
    op.create_table(
        'multimodal_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(length=32), nullable=False),
        sa.Column('storage_path', sa.String(length=256), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=64), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('provenance', sa.String(length=256), nullable=True),
        sa.Column('exif_sanitized', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_multimodal_assets_file_hash', 'multimodal_assets', ['file_hash'])
    op.create_index('ix_multimodal_assets_client_id', 'multimodal_assets', ['client_id'])

    # 2. Create multimodal_requests table
    op.create_table(
        'multimodal_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('input_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('multimodal_assets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('output_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('multimodal_assets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True)
    )
    op.create_index('ix_multimodal_requests_client_id', 'multimodal_requests', ['client_id'])

    # 3. Create multimodal_usage_events table
    op.create_table(
        'multimodal_usage_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('multimodal_requests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('feature', sa.String(length=32), nullable=False),
        sa.Column('unit_count', sa.Integer(), nullable=False),
        sa.Column('estimated_cost', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_multimodal_usage_events_client_id', 'multimodal_usage_events', ['client_id'])

    # 4. Create multimodal_policy_events table
    op.create_table(
        'multimodal_policy_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature', sa.String(length=32), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_multimodal_policy_events_client_id', 'multimodal_policy_events', ['client_id'])

    # 5. Add multimodal_asset_id column to agent_runs
    # Use batch_alter_table or check if batch is needed for sqlite compatibility
    with op.batch_alter_table('agent_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('multimodal_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('multimodal_assets.id', ondelete='SET NULL'), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('agent_runs', schema=None) as batch_op:
        batch_op.drop_column('multimodal_asset_id')

    op.drop_table('multimodal_policy_events')
    op.drop_table('multimodal_usage_events')
    op.drop_table('multimodal_requests')
    op.drop_table('multimodal_assets')
