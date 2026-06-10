"""Add prompt template variables, render events, and agent definition links

Revision ID: 20260530_0005
Revises: 20260530_0004
Create Date: 2026-05-30 11:00:00.000000

"""
from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0005'
down_revision: Optional[str] = '20260530_0004'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('prompt_templates'):
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
    prompt_indexes = {index['name'] for index in inspector.get_indexes('prompt_templates')} if inspector.has_table('prompt_templates') else set()
    if 'ix_prompt_templates_tenant_id' not in prompt_indexes:
        op.create_index('ix_prompt_templates_tenant_id', 'prompt_templates', ['tenant_id'])
    if 'ix_prompt_templates_name' not in prompt_indexes:
        op.create_index('ix_prompt_templates_name', 'prompt_templates', ['name'])

    if not inspector.has_table('prompt_template_versions'):
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
    version_indexes = {index['name'] for index in inspector.get_indexes('prompt_template_versions')} if inspector.has_table('prompt_template_versions') else set()
    if 'ix_prompt_template_versions_template_id' not in version_indexes:
        op.create_index('ix_prompt_template_versions_template_id', 'prompt_template_versions', ['template_id'])

    existing_fks = {fk['name'] for fk in inspector.get_foreign_keys('prompt_templates')} if inspector.has_table('prompt_templates') else set()
    if 'fk_prompt_templates_active_version' not in existing_fks:
        op.create_foreign_key(
            'fk_prompt_templates_active_version',
            'prompt_templates', 'prompt_template_versions',
            ['active_version_id'], ['id'],
            use_alter=True
        )

    if not inspector.has_table('prompt_experiments'):
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
    experiment_indexes = {index['name'] for index in inspector.get_indexes('prompt_experiments')} if inspector.has_table('prompt_experiments') else set()
    if 'ix_prompt_experiments_tenant_id' not in experiment_indexes:
        op.create_index('ix_prompt_experiments_tenant_id', 'prompt_experiments', ['tenant_id'])

    if not inspector.has_table('prompt_playground_runs'):
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

    if not inspector.has_table('prompt_template_variables'):
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
    variable_indexes = {index['name'] for index in inspector.get_indexes('prompt_template_variables')} if inspector.has_table('prompt_template_variables') else set()
    if 'ix_prompt_template_variables_template_id' not in variable_indexes:
        op.create_index('ix_prompt_template_variables_template_id', 'prompt_template_variables', ['template_id'])

    if not inspector.has_table('prompt_template_render_events'):
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
    render_indexes = {index['name'] for index in inspector.get_indexes('prompt_template_render_events')} if inspector.has_table('prompt_template_render_events') else set()
    if 'ix_prompt_template_render_events_template_id' not in render_indexes:
        op.create_index('ix_prompt_template_render_events_template_id', 'prompt_template_render_events', ['template_id'])
    if 'ix_prompt_template_render_events_version_id' not in render_indexes:
        op.create_index('ix_prompt_template_render_events_version_id', 'prompt_template_render_events', ['version_id'])
    if 'ix_prompt_template_render_events_tenant_id' not in render_indexes:
        op.create_index('ix_prompt_template_render_events_tenant_id', 'prompt_template_render_events', ['tenant_id'])
    if 'ix_prompt_template_render_events_agent_run_id' not in render_indexes:
        op.create_index('ix_prompt_template_render_events_agent_run_id', 'prompt_template_render_events', ['agent_run_id'])
    if 'ix_prompt_template_render_events_agent_id' not in render_indexes:
        op.create_index('ix_prompt_template_render_events_agent_id', 'prompt_template_render_events', ['agent_id'])

    agent_definition_columns = {column['name'] for column in inspector.get_columns('agent_definitions')} if inspector.has_table('agent_definitions') else set()
    if 'prompt_template_id' not in agent_definition_columns:
        op.add_column(
            'agent_definitions',
            sa.Column('prompt_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='SET NULL'), nullable=True),
        )
    if 'prompt_template_version_id' not in agent_definition_columns:
        op.add_column(
            'agent_definitions',
            sa.Column('prompt_template_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_template_versions.id', ondelete='SET NULL'), nullable=True),
        )
    agent_definition_indexes = {index['name'] for index in inspector.get_indexes('agent_definitions')} if inspector.has_table('agent_definitions') else set()
    if 'ix_agent_definitions_prompt_template_id' not in agent_definition_indexes:
        op.create_index('ix_agent_definitions_prompt_template_id', 'agent_definitions', ['prompt_template_id'])
    if 'ix_agent_definitions_prompt_template_version_id' not in agent_definition_indexes:
        op.create_index('ix_agent_definitions_prompt_template_version_id', 'agent_definitions', ['prompt_template_version_id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('agent_definitions'):
        indexes = {index['name'] for index in inspector.get_indexes('agent_definitions')}
        columns = {column['name'] for column in inspector.get_columns('agent_definitions')}
        if 'ix_agent_definitions_prompt_template_version_id' in indexes:
            op.drop_index('ix_agent_definitions_prompt_template_version_id', table_name='agent_definitions')
        if 'ix_agent_definitions_prompt_template_id' in indexes:
            op.drop_index('ix_agent_definitions_prompt_template_id', table_name='agent_definitions')
        if 'prompt_template_version_id' in columns:
            op.drop_column('agent_definitions', 'prompt_template_version_id')
        if 'prompt_template_id' in columns:
            op.drop_column('agent_definitions', 'prompt_template_id')
    for table_name in [
        'prompt_template_render_events',
        'prompt_template_variables',
        'prompt_playground_runs',
        'prompt_experiments',
        'prompt_template_versions',
        'prompt_templates',
    ]:
        if inspector.has_table(table_name):
            op.drop_table(table_name)
