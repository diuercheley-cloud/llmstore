# Models: AgentIncidentLink, AgentSLOWindow, AgentTraceLink
"""Agentic Observability End-to-End

Revision ID: phase88_agentic_observability_end_to_end
Revises: phase87_agent_eval_gates_refined
Create Date: 2026-05-22 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'phase88_agentic_observability_end_to_end'
down_revision: Union[str, None] = 'phase87_agent_eval_gates_refined'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. agent_incident_links
    op.create_table('agent_incident_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('linked_incident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('link_type', sa.String(length=32), nullable=False, server_default='related'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['agent_incidents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['linked_incident_id'], ['agent_incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_incident_links_incident_id'), 'agent_incident_links', ['incident_id'], unique=False)
    op.create_index(op.f('ix_agent_incident_links_linked_incident_id'), 'agent_incident_links', ['linked_incident_id'], unique=False)

    # 2. agent_slo_windows
    op.create_table('agent_slo_windows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('window_type', sa.String(length=32), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('slo_breached', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metrics_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_slo_windows_agent_id'), 'agent_slo_windows', ['agent_id'], unique=False)

    # 3. agent_trace_links
    op.create_table('agent_trace_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('linked_trace_id', sa.String(length=64), nullable=False),
        sa.Column('link_reason', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_trace_links_run_id'), 'agent_trace_links', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_trace_links_trace_id'), 'agent_trace_links', ['trace_id'], unique=False)
    op.create_index(op.f('ix_agent_trace_links_linked_trace_id'), 'agent_trace_links', ['linked_trace_id'], unique=False)

def downgrade() -> None:
    op.drop_table('agent_trace_links')
    op.drop_table('agent_slo_windows')
    op.drop_table('agent_incident_links')
