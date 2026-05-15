"""geo_routing_fields

Revision ID: 20260514_0040
Revises: 20260514_0039_cross_cluster_forwarding
Create Date: 2026-05-14 16:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260514_0040'
down_revision = '20260514_0039_cross_cluster_forwarding'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('commercial_cluster_registry', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('datacenter', sa.String(length=64), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('continent', sa.String(length=32), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('country', sa.String(length=32), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('region_group', sa.String(length=64), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('avg_public_latency_ms', sa.Integer(), nullable=True))
    op.add_column('commercial_cluster_registry', sa.Column('geo_metadata_json', sa.JSON(), nullable=True))
    
    op.create_index(op.f('ix_commercial_cluster_registry_region_group'), 'commercial_cluster_registry', ['region_group'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_commercial_cluster_registry_region_group'), table_name='commercial_cluster_registry')
    op.drop_column('commercial_cluster_registry', 'geo_metadata_json')
    op.drop_column('commercial_cluster_registry', 'avg_public_latency_ms')
    op.drop_column('commercial_cluster_registry', 'region_group')
    op.drop_column('commercial_cluster_registry', 'country')
    op.drop_column('commercial_cluster_registry', 'continent')
    op.drop_column('commercial_cluster_registry', 'datacenter')
    op.drop_column('commercial_cluster_registry', 'longitude')
    op.drop_column('commercial_cluster_registry', 'latitude')
