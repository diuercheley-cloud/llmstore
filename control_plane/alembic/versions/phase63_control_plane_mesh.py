"""Phase 63 Control Plane Mesh

Revision ID: phase63_control_plane_mesh
Revises: 2866e45907ab
Create Date: 2026-05-15 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'phase63_control_plane_mesh'
down_revision = '2866e45907ab'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # CommercialMeshNode
    op.create_table('commercial_mesh_nodes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('region', sa.String(), nullable=True),
        sa.Column('mode', sa.String(), nullable=True, server_default='multi_region'),
        sa.Column('public_key', sa.String(), nullable=True),
        sa.Column('is_leader', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('status', sa.String(), nullable=True, server_default='active'),
        sa.Column('metadata_', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_mesh_nodes_name'), 'commercial_mesh_nodes', ['name'], unique=True)
    op.create_index(op.f('ix_commercial_mesh_nodes_region'), 'commercial_mesh_nodes', ['region'], unique=False)

    # CommercialMeshConsensusEvent
    op.create_table('commercial_mesh_consensus_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('term', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('proposer_node_id', sa.String(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('signature', sa.String(), nullable=True),
        sa.Column('quorum_reached', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['proposer_node_id'], ['commercial_mesh_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_mesh_consensus_events_term'), 'commercial_mesh_consensus_events', ['term'], unique=False)

    # CommercialMeshReplicationLog
    op.create_table('commercial_mesh_replication_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('log_index', sa.Integer(), nullable=True),
        sa.Column('operation', sa.String(), nullable=True),
        sa.Column('target_entity', sa.String(), nullable=True),
        sa.Column('target_id', sa.String(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('hash_signature', sa.String(), nullable=True),
        sa.Column('applied', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['node_id'], ['commercial_mesh_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_mesh_replication_logs_log_index'), 'commercial_mesh_replication_logs', ['log_index'], unique=False)

    # CommercialMeshHealthState
    op.create_table('commercial_mesh_health_states',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('node_id', sa.String(), nullable=True),
        sa.Column('peer_node_id', sa.String(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['node_id'], ['commercial_mesh_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # CommercialMeshPartitionEvent
    op.create_table('commercial_mesh_partition_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('partition_id', sa.String(), nullable=True),
        sa.Column('isolated_nodes', sa.JSON(), nullable=True),
        sa.Column('mode_fallback', sa.String(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_details', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_mesh_partition_events_partition_id'), 'commercial_mesh_partition_events', ['partition_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_commercial_mesh_partition_events_partition_id'), table_name='commercial_mesh_partition_events')
    op.drop_table('commercial_mesh_partition_events')
    op.drop_table('commercial_mesh_health_states')
    op.drop_index(op.f('ix_commercial_mesh_replication_logs_log_index'), table_name='commercial_mesh_replication_logs')
    op.drop_table('commercial_mesh_replication_logs')
    op.drop_index(op.f('ix_commercial_mesh_consensus_events_term'), table_name='commercial_mesh_consensus_events')
    op.drop_table('commercial_mesh_consensus_events')
    op.drop_index(op.f('ix_commercial_mesh_nodes_region'), table_name='commercial_mesh_nodes')
    op.drop_index(op.f('ix_commercial_mesh_nodes_name'), table_name='commercial_mesh_nodes')
    op.drop_table('commercial_mesh_nodes')
