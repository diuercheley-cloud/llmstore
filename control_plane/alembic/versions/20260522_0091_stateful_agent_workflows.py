# Models: AgentWorkflow, AgentWorkflowRun, AgentWorkflowEvent, AgentWorkflowTimer, AgentWorkflowSignal, AgentWorkflowWebhookWait, AgentWorkflowLock
"""stateful agent workflows

Revision ID: 20260522_0091
Revises: phase90_agent_supply_chain
Create Date: 2026-05-22 19:30:00.000000

"""
from typing import Sequence, Optional

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260522_0091'
down_revision: Optional[str] = 'phase90_agent_supply_chain'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. agent_workflows
    op.create_table(
        'agent_workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workflows_tenant_id'), 'agent_workflows', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agent_workflows_status'), 'agent_workflows', ['status'], unique=False)

    # 2. agent_workflow_runs
    op.create_table(
        'agent_workflow_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('current_state', sa.String(length=64), nullable=False),
        sa.Column('state_data', sa.JSON(), nullable=False),
        sa.Column('context', sa.JSON(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('next_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lease_owner', sa.String(length=128), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workflow_id'], ['agent_workflows.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workflow_runs_workflow_id'), 'agent_workflow_runs', ['workflow_id'], unique=False)
    op.create_index(op.f('ix_agent_workflow_runs_tenant_id'), 'agent_workflow_runs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agent_workflow_runs_status'), 'agent_workflow_runs', ['status'], unique=False)
    op.create_index(op.f('ix_agent_workflow_runs_next_execution_at'), 'agent_workflow_runs', ['next_execution_at'], unique=False)

    # 3. agent_workflow_events
    op.create_table(
        'agent_workflow_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('from_state', sa.String(length=64), nullable=True),
        sa.Column('to_state', sa.String(length=64), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workflow_events_run_id'), 'agent_workflow_events', ['run_id'], unique=False)

    # 4. agent_workflow_timers
    op.create_table(
        'agent_workflow_timers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('timer_name', sa.String(length=128), nullable=False),
        sa.Column('fire_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workflow_timers_run_id'), 'agent_workflow_timers', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_workflow_timers_fire_at'), 'agent_workflow_timers', ['fire_at'], unique=False)

    # 5. agent_workflow_signals
    op.create_table(
        'agent_workflow_signals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('signal_name', sa.String(length=128), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workflow_signals_run_id'), 'agent_workflow_signals', ['run_id'], unique=False)

    # 6. agent_workflow_webhook_waits
    op.create_table(
        'agent_workflow_webhook_waits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('webhook_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('received_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_workflow_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workflow_webhook_waits_run_id'), 'agent_workflow_webhook_waits', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_workflow_webhook_waits_webhook_id'), 'agent_workflow_webhook_waits', ['webhook_id'], unique=False)

    # 7. agent_workflow_locks
    op.create_table(
        'agent_workflow_locks',
        sa.Column('lock_key', sa.String(length=256), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('lock_key')
    )


def downgrade() -> None:
    op.drop_table('agent_workflow_locks')
    op.drop_table('agent_workflow_webhook_waits')
    op.drop_table('agent_workflow_signals')
    op.drop_table('agent_workflow_timers')
    op.drop_table('agent_workflow_events')
    op.drop_table('agent_workflow_runs')
    op.drop_table('agent_workflows')
