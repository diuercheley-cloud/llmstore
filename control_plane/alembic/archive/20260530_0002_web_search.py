"""Add agent web search tables

Revision ID: 20260530_0002
Revises: 20260530_0001
Create Date: 2026-05-30 09:00:00.000000

"""
from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0002'
down_revision: Optional[str] = '20260530_0001'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. Create agent_web_search_queries table
    op.create_table(
        'agent_web_search_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_definitions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_agent_web_search_queries_run_id', 'agent_web_search_queries', ['run_id'])
    op.create_index('ix_agent_web_search_queries_agent_id', 'agent_web_search_queries', ['agent_id'])
    op.create_index('ix_agent_web_search_queries_tenant_id', 'agent_web_search_queries', ['tenant_id'])
    op.create_index('ix_agent_web_search_queries_query_hash', 'agent_web_search_queries', ['query_hash'])

    # 2. Create agent_web_search_results table
    op.create_table(
        'agent_web_search_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_web_search_queries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('snippet', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_agent_web_search_results_query_id', 'agent_web_search_results', ['query_id'])

    # 3. Create agent_web_search_cache table
    op.create_table(
        'agent_web_search_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('results_json', sa.JSON(), nullable=False),
        sa.Column('ttl_seconds', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_agent_web_search_cache_query_hash', 'agent_web_search_cache', ['query_hash'], unique=True)

    # 4. Create agent_web_search_policy_events table
    op.create_table(
        'agent_web_search_policy_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_definitions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_agent_web_search_policy_events_tenant_id', 'agent_web_search_policy_events', ['tenant_id'])
    op.create_index('ix_agent_web_search_policy_events_agent_id', 'agent_web_search_policy_events', ['agent_id'])


def downgrade() -> None:
    op.drop_table('agent_web_search_policy_events')
    op.drop_table('agent_web_search_cache')
    op.drop_table('agent_web_search_results')
    op.drop_table('agent_web_search_queries')
