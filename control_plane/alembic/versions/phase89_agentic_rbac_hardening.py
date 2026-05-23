# Models: AgentEnvironmentPolicy, AgentEphemeralCredential, AgentRBACEvent, AgentPolicyException
"""Agentic RBAC and Policies

Revision ID: phase89_agentic_rbac_hardening
Revises: phase88_agentic_observability
Create Date: 2026-05-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'phase89_agentic_rbac_hardening'
down_revision: Union[str, None] = 'phase88_agentic_observability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. agent_environment_policies
    op.create_table('agent_environment_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=True),
        sa.Column('environment', sa.String(length=32), nullable=False),
        sa.Column('config_json', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_environment_policies_tenant_id'), 'agent_environment_policies', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agent_environment_policies_environment'), 'agent_environment_policies', ['environment'], unique=False)

    # 2. agent_ephemeral_credentials
    op.create_table('agent_ephemeral_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope', sa.String(length=128), nullable=False),
        sa.Column('credential_type', sa.String(length=32), nullable=False),
        sa.Column('credential_value', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_ephemeral_credentials_run_id'), 'agent_ephemeral_credentials', ['run_id'], unique=False)

    # 3. agent_rbac_events
    op.create_table('agent_rbac_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('permission_code', sa.String(length=128), nullable=True),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('actor_identifier', sa.String(length=128), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['admin_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_rbac_events_admin_user_id'), 'agent_rbac_events', ['admin_user_id'], unique=False)

    # 4. agent_policy_exceptions
    op.create_table('agent_policy_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_type', sa.String(length=64), nullable=False),
        sa.Column('exception_reason', sa.Text(), nullable=False),
        sa.Column('approved_by', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_policy_exceptions_agent_id'), 'agent_policy_exceptions', ['agent_id'], unique=False)

def downgrade() -> None:
    op.drop_table('agent_policy_exceptions')
    op.drop_table('agent_rbac_events')
    op.drop_table('agent_ephemeral_credentials')
    op.drop_table('agent_environment_policies')
