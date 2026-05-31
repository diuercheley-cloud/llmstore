"""Add prompt template variables, render events, and agent definition links

Revision ID: 20260530_0005
Revises: 20260530_0004
Create Date: 2026-05-30 11:00:00.000000

"""
from typing import Sequence, Optional

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0005'
down_revision: Optional[str] = '20260530_0004'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 0. Create prompt_templates
    op.create_table(
        'prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('variable_schema', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('active_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_prompt_templates_tenant_id', 'prompt_templates', ['tenant_id'])
    op.create_index('ix_prompt_templates_name', 'prompt_templates', ['name'])

    # 0.1 Create prompt_template_versions
    op.create_table(
        'prompt_template_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_tag', sa.String(length=64), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('provider_settings', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_prompt_template_versions_template_id', 'prompt_template_versions', ['template_id'])

    # 0.2 Add ForeignKey with use_alter for active_version_id
    op.create_foreign_key(
        'fk_prompt_templates_active_version',
        'prompt_templates', 'prompt_template_versions',
        ['active_version_id'], ['id'],
        use_alter=True
    )

    # 0.3 Create prompt_experiments
    op.create_table(
        'prompt_experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_a_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id'), nullable=False),
        sa.Column('version_b_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='running'),
        sa.Column('traffic_split', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('winner_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_prompt_experiments_tenant_id', 'prompt_experiments', ['tenant_id'])

    # 0.4 Create prompt_playground_runs
    op.create_table(
        'prompt_playground_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('output', sa.Text(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('token_usage', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 1. Create prompt_template_variables
    op.create_table(
        'prompt_template_variables',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('var_type', sa.String(length=32), nullable=False, server_default='string'),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_prompt_template_variables_template_id', 'prompt_template_variables', ['template_id'])

    # 2. Create prompt_template_render_events
    op.create_table(
        'prompt_template_render_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('variables_hash', sa.String(length=128), nullable=False),
        sa.Column('output_hash', sa.String(length=128), nullable=False),
        sa.Column('rendered_content_hash', sa.String(length=128), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_definitions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_prompt_template_render_events_template_id', 'prompt_template_render_events', ['template_id'])
    op.create_index('ix_prompt_template_render_events_version_id', 'prompt_template_render_events', ['version_id'])
    op.create_index('ix_prompt_template_render_events_tenant_id', 'prompt_template_render_events', ['tenant_id'])
    op.create_index('ix_prompt_template_render_events_agent_run_id', 'prompt_template_render_events', ['agent_run_id'])
    op.create_index('ix_prompt_template_render_events_agent_id', 'prompt_template_render_events', ['agent_id'])

    # 3. Add prompt_template columns to agent_definitions
    # Use batch_alter_table for sqlite compatibility if needed, but this script seems aimed at postgres
    op.add_column(
        'agent_definitions',
        sa.Column('prompt_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='SET NULL'), nullable=True),
    )
    op.add_column(
        'agent_definitions',
        sa.Column('prompt_template_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_agent_definitions_prompt_template_id', 'agent_definitions', ['prompt_template_id'])
    op.create_index('ix_agent_definitions_prompt_template_version_id', 'agent_definitions', ['prompt_template_version_id'])


def downgrade() -> None:
    op.drop_index('ix_agent_definitions_prompt_template_version_id', table_name='agent_definitions')
    op.drop_index('ix_agent_definitions_prompt_template_id', table_name='agent_definitions')
    op.drop_column('agent_definitions', 'prompt_template_version_id')
    op.drop_column('agent_definitions', 'prompt_template_id')
    op.drop_table('prompt_template_render_events')
    op.drop_table('prompt_template_variables')
    op.drop_table('prompt_playground_runs')
    op.drop_table('prompt_experiments')
    op.drop_table('prompt_template_versions')
    op.drop_table('prompt_templates')
