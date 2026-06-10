"""gpu orchestration and autoscaling

Revision ID: 20260519_0086
Revises: 20260519_0085
Create Date: 2026-05-19 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260519_0086'
down_revision: Union[str, None] = '20260519_0085'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # gpu_devices
    op.create_table(
        'gpu_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('runtime_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gpu_index', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('memory_total_mb', sa.Integer(), nullable=True),
        sa.Column('memory_used_mb', sa.Integer(), nullable=True),
        sa.Column('utilization_percent', sa.Float(), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['runtime_node_id'], ['runtime_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gpu_devices_runtime_node_id'), 'gpu_devices', ['runtime_node_id'], unique=False)

    # gpu_allocations
    op.create_table(
        'gpu_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gpu_device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_registry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allocated_memory_mb', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['gpu_device_id'], ['gpu_devices.id'], ),
        sa.ForeignKeyConstraint(['model_registry_id'], ['model_registry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gpu_allocations_gpu_device_id'), 'gpu_allocations', ['gpu_device_id'], unique=False)

    # gpu_capacity_snapshots
    op.create_table(
        'gpu_capacity_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('runtime_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_memory_mb', sa.Integer(), nullable=False),
        sa.Column('used_memory_mb', sa.Integer(), nullable=False),
        sa.Column('avg_utilization_percent', sa.Float(), nullable=False),
        sa.Column('gpu_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['runtime_node_id'], ['runtime_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gpu_capacity_snapshots_runtime_node_id'), 'gpu_capacity_snapshots', ['runtime_node_id'], unique=False)

    # autoscaling_policies
    op.create_table(
        'autoscaling_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_registry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('strategy', sa.String(length=64), nullable=True),
        sa.Column('min_replicas', sa.Integer(), nullable=True),
        sa.Column('max_replicas', sa.Integer(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('cooldown_seconds', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('mode', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['model_registry_id'], ['model_registry.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_autoscaling_policies_model_registry_id'), 'autoscaling_policies', ['model_registry_id'], unique=False)

    # autoscaling_events
    op.create_table(
        'autoscaling_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=True),
        sa.Column('reason', sa.String(length=1024), nullable=True),
        sa.Column('replicas_before', sa.Integer(), nullable=True),
        sa.Column('replicas_after', sa.Integer(), nullable=True),
        sa.Column('metrics_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['autoscaling_policies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_autoscaling_events_policy_id'), 'autoscaling_events', ['policy_id'], unique=False)


def downgrade() -> None:
    op.drop_table('autoscaling_events')
    op.drop_table('autoscaling_policies')
    op.drop_table('gpu_capacity_snapshots')
    op.drop_table('gpu_allocations')
    op.drop_table('gpu_devices')
