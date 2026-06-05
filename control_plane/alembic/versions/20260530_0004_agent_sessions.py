"""Add agent sessions and conversation threads

Revision ID: 20260530_0004
Revises: 20260530_0003
Create Date: 2026-05-30 10:00:00.000000

"""
from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0004'
down_revision: Optional[str] = '20260530_0003'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('agent_sessions'):
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

    session_indexes = {index['name'] for index in inspector.get_indexes('agent_sessions')} if inspector.has_table('agent_sessions') else set()
    if 'ix_agent_sessions_tenant_id' not in session_indexes:
        op.create_index('ix_agent_sessions_tenant_id', 'agent_sessions', ['tenant_id'])
    if 'ix_agent_sessions_agent_id' not in session_indexes:
        op.create_index('ix_agent_sessions_agent_id', 'agent_sessions', ['agent_id'])
    if 'ix_agent_sessions_status' not in session_indexes:
        op.create_index('ix_agent_sessions_status', 'agent_sessions', ['status'])
    if 'ix_agent_sessions_last_message_at' not in session_indexes:
        op.create_index('ix_agent_sessions_last_message_at', 'agent_sessions', ['last_message_at'])

    if not inspector.has_table('agent_conversation_threads'):
        op.create_table(
            'agent_conversation_threads',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('title', sa.String(length=256), nullable=True),
            sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
    thread_indexes = {index['name'] for index in inspector.get_indexes('agent_conversation_threads')} if inspector.has_table('agent_conversation_threads') else set()
    if 'ix_agent_conversation_threads_session_id' not in thread_indexes:
        op.create_index('ix_agent_conversation_threads_session_id', 'agent_conversation_threads', ['session_id'])

    if not inspector.has_table('agent_thread_messages'):
        op.create_table(
            'agent_thread_messages',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_conversation_threads.id', ondelete='CASCADE'), nullable=False),
            sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('role', sa.String(length=32), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('content_hash', sa.String(length=128), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
    message_indexes = {index['name'] for index in inspector.get_indexes('agent_thread_messages')} if inspector.has_table('agent_thread_messages') else set()
    if 'ix_agent_thread_messages_thread_id' not in message_indexes:
        op.create_index('ix_agent_thread_messages_thread_id', 'agent_thread_messages', ['thread_id'])
    if 'ix_agent_thread_messages_session_id' not in message_indexes:
        op.create_index('ix_agent_thread_messages_session_id', 'agent_thread_messages', ['session_id'])
    if 'ix_agent_thread_messages_run_id' not in message_indexes:
        op.create_index('ix_agent_thread_messages_run_id', 'agent_thread_messages', ['run_id'])
    if 'ix_agent_thread_messages_created_at' not in message_indexes:
        op.create_index('ix_agent_thread_messages_created_at', 'agent_thread_messages', ['created_at'])

    if not inspector.has_table('agent_session_runs'):
        op.create_table(
            'agent_session_runs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
    session_run_indexes = {index['name'] for index in inspector.get_indexes('agent_session_runs')} if inspector.has_table('agent_session_runs') else set()
    if 'ix_agent_session_runs_session_id' not in session_run_indexes:
        op.create_index('ix_agent_session_runs_session_id', 'agent_session_runs', ['session_id'])
    if 'ix_agent_session_runs_run_id' not in session_run_indexes:
        op.create_index('ix_agent_session_runs_run_id', 'agent_session_runs', ['run_id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('agent_session_runs'):
        op.drop_table('agent_session_runs')
    if inspector.has_table('agent_thread_messages'):
        op.drop_table('agent_thread_messages')
    if inspector.has_table('agent_conversation_threads'):
        op.drop_table('agent_conversation_threads')
    if inspector.has_table('agent_sessions'):
        op.drop_table('agent_sessions')
