"""Add cross cluster forwarding fields

Revision ID: 20260514_0039
Revises: 20260514_0038_global_traffic
Create Date: 2026-05-14 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260514_0039'
down_revision = '20260514_0038'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add columns to commercial_cluster_registry
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_base_url', sa.String(length=500), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_public_key', sa.String(length=2048), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_jwt_audience', sa.String(length=255), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_require_mtls', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_status', sa.String(length=32), server_default='healthy', nullable=False))
    op.add_column('commercial_cluster_registry', sa.Column('forwarding_metadata_json', sa.JSON(), nullable=True))

    # Create commercial_cross_cluster_forwarding_event table
    op.create_table('commercial_cross_cluster_forwarding_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_cluster_id', sa.String(length=128), nullable=False),
        sa.Column('target_cluster_id', sa.String(length=128), nullable=False),
        sa.Column('correlation_id', sa.String(length=128), nullable=True),
        sa.Column('request_mode', sa.String(length=32), nullable=False),
        sa.Column('result', sa.String(length=64), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('bytes_out', sa.Integer(), nullable=False),
        sa.Column('bytes_in', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_cross_cluster_forwarding_event_source_cluster_id'), 'commercial_cross_cluster_forwarding_event', ['source_cluster_id'], unique=False)
    op.create_index(op.f('ix_commercial_cross_cluster_forwarding_event_target_cluster_id'), 'commercial_cross_cluster_forwarding_event', ['target_cluster_id'], unique=False)
    op.create_index(op.f('ix_commercial_cross_cluster_forwarding_event_correlation_id'), 'commercial_cross_cluster_forwarding_event', ['correlation_id'], unique=False)
    op.create_index(op.f('ix_commercial_cross_cluster_forwarding_event_created_at'), 'commercial_cross_cluster_forwarding_event', ['created_at'], unique=False)

def downgrade() -> None:
    # Drop table
    op.drop_index(op.f('ix_commercial_cross_cluster_forwarding_event_created_at'), table_name='commercial_cross_cluster_forwarding_event')
    op.drop_index(op.f('ix_commercial_cross_cluster_forwarding_event_correlation_id'), table_name='commercial_cross_cluster_forwarding_event')
    op.drop_index(op.f('ix_commercial_cross_cluster_forwarding_event_target_cluster_id'), table_name='commercial_cross_cluster_forwarding_event')
    op.drop_index(op.f('ix_commercial_cross_cluster_forwarding_event_source_cluster_id'), table_name='commercial_cross_cluster_forwarding_event')
    op.drop_table('commercial_cross_cluster_forwarding_event')

    # Drop columns
    op.drop_column('commercial_cluster_registry', 'forwarding_metadata_json')
    op.drop_column('commercial_cluster_registry', 'forwarding_status')
    op.drop_column('commercial_cluster_registry', 'forwarding_require_mtls')
    op.drop_column('commercial_cluster_registry', 'forwarding_jwt_audience')
    op.drop_column('commercial_cluster_registry', 'forwarding_public_key')
    op.drop_column('commercial_cluster_registry', 'forwarding_base_url')
    op.drop_column('commercial_cluster_registry', 'forwarding_enabled')
