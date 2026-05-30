"""Add agent sessions and conversation threads

Revision ID: 20260530_0004
Revises: 20260530_0003
Create Date: 2026-05-30 10:00:00.000000

"""
from typing import Sequence, Optional

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0004'
down_revision: Optional[str] = '20260530_0003'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. Create agent_sessions table
    op.create_table(
        'agent_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_definitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('retention_policy', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_agent_sessions_tenant_id', 'agent_sessions', ['tenant_id'])
    op.create_index('ix_agent_sessions_agent_id', 'agent_sessions', ['agent_id'])
    op.create_index('ix_agent_sessions_status', 'agent_sessions', ['status'])
    op.create_index('ix_agent_sessions_last_message_at', 'agent_sessions', ['last_message_at'])

    # 2. Create agent_conversation_threads table
    op.create_table(
        'agent_conversation_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_agent_conversation_threads_session_id', 'agent_conversation_threads', ['session_id'])

    # 3. Create agent_thread_messages table
    op.create_table(
        'agent_thread_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_conversation_threads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_agent_thread_messages_thread_id', 'agent_thread_messages', ['thread_id'])
    op.create_index('ix_agent_thread_messages_session_id', 'agent_thread_messages', ['session_id'])
    op.create_index('ix_agent_thread_messages_run_id', 'agent_thread_messages', ['run_id'])
    op.create_index('ix_agent_thread_messages_created_at', 'agent_thread_messages', ['created_at'])

    # 4. Create agent_session_runs table
    op.create_table(
        'agent_session_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_agent_session_runs_session_id', 'agent_session_runs', ['session_id'])
    op.create_index('ix_agent_session_runs_run_id', 'agent_session_runs', ['run_id'])

    # 5. Create agent_session_summaries table
    op.create_table(
        'agent_session_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(length=128), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_agent_session_summaries_session_id', 'agent_session_summaries', ['session_id'])

    # 6. Add session_id column to agent_runs
    op.add_column(
        'agent_runs',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_agent_runs_session_id', 'agent_runs', ['session_id'])


def downgrade() -> None:
    op.drop_index('ix_agent_runs_session_id', table_name='agent_runs')
    op.drop_column('agent_runs', 'session_id')
    op.drop_table('agent_session_summaries')
    op.drop_table('agent_session_runs')
    op.drop_table('agent_thread_messages')
    op.drop_table('agent_conversation_threads')
    op.drop_table('agent_sessions')
