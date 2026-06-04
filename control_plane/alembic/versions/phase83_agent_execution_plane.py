# Models: AgentExecutionJob, AgentWorkerHeartbeat, AgentExecutionLease, AgentExecutionRetry, AgentExecutionDeadLetter
"""Agent Execution Plane tables

Revision ID: phase83_agent_execution_plane
Revises: 6c73eca75cd9
Create Date: 2026-05-22 12:22:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'phase83_agent_execution_plane'
down_revision: Union[str, None] = 'phase82_9_agent_core'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_execution_jobs
    op.create_table('agent_execution_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('backoff_factor', sa.Float(), nullable=False),
        sa.Column('initial_delay_seconds', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_execution_jobs_agent_id'), 'agent_execution_jobs', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_execution_jobs_agent_run_id'), 'agent_execution_jobs', ['agent_run_id'], unique=False)
    op.create_index(op.f('ix_agent_execution_jobs_status'), 'agent_execution_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_agent_execution_jobs_tenant_id'), 'agent_execution_jobs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agent_execution_jobs_scheduled_at'), 'agent_execution_jobs', ['scheduled_at'], unique=False)

    # 2. agent_worker_heartbeats
    op.create_table('agent_worker_heartbeats',
        sa.Column('worker_id', sa.String(length=128), nullable=False),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('worker_id')
    )

    # 3. agent_execution_leases
    op.create_table('agent_execution_leases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('worker_id', sa.String(length=128), nullable=False),
        sa.Column('leased_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['agent_execution_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_execution_leases_job_id'), 'agent_execution_leases', ['job_id'], unique=True)
    op.create_index(op.f('ix_agent_execution_leases_worker_id'), 'agent_execution_leases', ['worker_id'], unique=False)
    op.create_index(op.f('ix_agent_execution_leases_expires_at'), 'agent_execution_leases', ['expires_at'], unique=False)

    # 4. agent_execution_retries
    op.create_table('agent_execution_retries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['agent_execution_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_execution_retries_job_id'), 'agent_execution_retries', ['job_id'], unique=False)

    # 5. agent_execution_dead_letters
    op.create_table('agent_execution_dead_letters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_execution_dead_letters_job_id'), 'agent_execution_dead_letters', ['job_id'], unique=False)
    op.create_index(op.f('ix_agent_execution_dead_letters_tenant_id'), 'agent_execution_dead_letters', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_execution_dead_letters')
    op.drop_table('agent_execution_retries')
    op.drop_table('agent_execution_leases')
    op.drop_table('agent_worker_heartbeats')
    op.drop_table('agent_execution_jobs')
