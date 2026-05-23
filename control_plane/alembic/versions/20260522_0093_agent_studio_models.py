# Models: AgentFlowDefinition, AgentFlowVersion, AgentFlowNode, AgentFlowEdge, AgentDebugSession, AgentDebugEvent
"""agent studio models

Revision ID: 20260522_0093
Revises: 20260522_0092
Create Date: 2026-05-22 21:00:00.000000

"""
from typing import Sequence, Optional

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260522_0093'
down_revision: Optional[str] = '20260522_0092'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. agent_flow_definitions
    op.create_table(
        'agent_flow_definitions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_flow_definitions_tenant_id'), 'agent_flow_definitions', ['tenant_id'], unique=False)

    # 2. agent_flow_versions
    op.create_table(
        'agent_flow_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('flow_id', sa.UUID(), nullable=False),
        sa.Column('version_label', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('graph_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['flow_id'], ['agent_flow_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_flow_versions_flow_id'), 'agent_flow_versions', ['flow_id'], unique=False)

    # 3. agent_flow_nodes
    op.create_table(
        'agent_flow_nodes',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('version_id', sa.UUID(), nullable=False),
        sa.Column('node_type', sa.String(length=64), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('position_x', sa.Float(), nullable=False),
        sa.Column('position_y', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['agent_flow_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', 'version_id')
    )

    # 4. agent_flow_edges
    op.create_table(
        'agent_flow_edges',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('version_id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.String(length=128), nullable=False),
        sa.Column('target_node_id', sa.String(length=128), nullable=False),
        sa.Column('condition', sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(['version_id'], ['agent_flow_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', 'version_id')
    )

    # 5. agent_debug_sessions
    op.create_table(
        'agent_debug_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=True),
        sa.Column('flow_version_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['flow_version_id'], ['agent_flow_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_debug_sessions_run_id'), 'agent_debug_sessions', ['run_id'], unique=False)

    # 6. agent_debug_events
    op.create_table(
        'agent_debug_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('node_id', sa.String(length=128), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['agent_debug_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_debug_events_session_id'), 'agent_debug_events', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_debug_events')
    op.drop_table('agent_debug_sessions')
    op.drop_table('agent_flow_edges')
    op.drop_table('agent_flow_nodes')
    op.drop_table('agent_flow_versions')
    op.drop_table('agent_flow_definitions')
