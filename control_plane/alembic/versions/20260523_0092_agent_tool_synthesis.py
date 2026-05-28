"""Add agent tool synthesis models

Revision ID: 20260523_0092
Revises: 20260522_0091
Create Date: 2026-05-23 10:00:00.000000

"""
# Model class: AgentSandboxPolicyEvent
# Model class: AgentGeneratedTool
# Model class: AgentGeneratedToolVersion
# Model class: AgentCodeInterpreterRun
# Model class: AgentSandboxSession
# Model class: AgentSandboxArtifact
from typing import Sequence, Optional

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260523_0092'
down_revision: Optional[str] = '20260522_0091'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        'agent_generated_tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('author_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_agent_generated_tools_name', 'agent_generated_tools', ['name'])

    op.create_table(
        'agent_generated_tool_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_generated_tools.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_tag', sa.String(length=64), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('schema_json', sa.JSON(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    op.create_table(
        'agent_sandbox_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        'agent_code_interpreter_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sandbox_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('stdout', sa.Text(), nullable=True),
        sa.Column('stderr', sa.Text(), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    op.create_table(
        'agent_sandbox_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sandbox_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(length=256), nullable=False),
        sa.Column('content_type', sa.String(length=64), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    op.create_table(
        'agent_sandbox_policy_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sandbox_sessions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('agent_sandbox_policy_events')
    op.drop_table('agent_sandbox_artifacts')
    op.drop_table('agent_code_interpreter_runs')
    op.drop_table('agent_sandbox_sessions')
    op.drop_table('agent_generated_tool_versions')
    op.drop_index('ix_agent_generated_tools_name', 'agent_generated_tools')
    op.drop_table('agent_generated_tools')
