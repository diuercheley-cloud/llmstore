# Models: AgentTeam, AgentTeamMember, AgentTeamRun, AgentTeamMessage, AgentTeamDelegation, AgentSharedWorkspace, AgentTeamTrace
"""multi agent orchestration

Revision ID: 20260522_0092
Revises: 20260522_0091
Create Date: 2026-05-22 20:00:00.000000

"""
from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260522_0092'
down_revision: Optional[str] = '20260522_0091'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. agent_teams
    op.create_table(
        'agent_teams',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('topology', sa.String(length=64), nullable=False),
        sa.Column('owner_user_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_teams_tenant_id'), 'agent_teams', ['tenant_id'], unique=False)

    # 2. agent_team_members
    op.create_table(
        'agent_team_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=64), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['agent_teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_team_members_team_id'), 'agent_team_members', ['team_id'], unique=False)

    # 3. agent_team_runs
    op.create_table(
        'agent_team_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('team_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('input_goal', sa.Text(), nullable=False),
        sa.Column('output_result', sa.Text(), nullable=True),
        sa.Column('current_round', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['agent_teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_team_runs_team_id'), 'agent_team_runs', ['team_id'], unique=False)
    op.create_index(op.f('ix_agent_team_runs_tenant_id'), 'agent_team_runs', ['tenant_id'], unique=False)

    # 4. agent_team_messages
    op.create_table(
        'agent_team_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('sender_agent_id', sa.UUID(), nullable=True),
        sa.Column('recipient_agent_id', sa.UUID(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['recipient_agent_id'], ['agent_definitions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_team_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_agent_id'], ['agent_definitions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_team_messages_run_id'), 'agent_team_messages', ['run_id'], unique=False)

    # 5. agent_team_delegations
    op.create_table(
        'agent_team_delegations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('parent_agent_id', sa.UUID(), nullable=False),
        sa.Column('child_agent_id', sa.UUID(), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['child_agent_id'], ['agent_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_agent_id'], ['agent_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_team_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_team_delegations_run_id'), 'agent_team_delegations', ['run_id'], unique=False)

    # 6. agent_shared_workspaces
    op.create_table(
        'agent_shared_workspaces',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('team_run_id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=256), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['team_run_id'], ['agent_team_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_shared_workspaces_tenant_id'), 'agent_shared_workspaces', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agent_shared_workspaces_team_run_id'), 'agent_shared_workspaces', ['team_run_id'], unique=False)

    # 7. agent_team_traces
    op.create_table(
        'agent_team_traces',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_team_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_team_traces_run_id'), 'agent_team_traces', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_team_traces')
    op.drop_table('agent_shared_workspaces')
    op.drop_table('agent_team_delegations')
    op.drop_table('agent_team_messages')
    op.drop_table('agent_team_runs')
    op.drop_table('agent_team_members')
    op.drop_table('agent_teams')
