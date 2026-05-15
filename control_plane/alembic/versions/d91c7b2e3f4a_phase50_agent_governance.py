"""phase50_agent_governance

Revision ID: d91c7b2e3f4a
Revises: 31a7b456d2e1
Create Date: 2026-05-15 14:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd91c7b2e3f4a'
down_revision = ('31a7b456d2e1', '20260515_0062')
branch_labels = None
depends_on = None


def upgrade():
    # 1. CommercialAgentProfile
    op.create_table(
        'commercial_agent_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_name', sa.String(length=128), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('base_model', sa.String(length=255), nullable=True),
        sa.Column('allowed_tools', sa.JSON(), nullable=True),
        sa.Column('system_prompt_hash', sa.String(length=128), nullable=True),
        sa.Column('requires_approval_for_tools', sa.Boolean(), nullable=True),
        sa.Column('can_delegate', sa.Boolean(), nullable=True),
        sa.Column('max_delegation_depth', sa.Integer(), nullable=True),
        sa.Column('memory_isolation_mode', sa.String(length=32), nullable=True),
        sa.Column('confidential_runtime_required', sa.Boolean(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_agent_profiles_client_id'), 'commercial_agent_profiles', ['client_id'], unique=False)

    # 2. CommercialAgentExecution
    op.create_table(
        'commercial_agent_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=True),
        sa.Column('parent_execution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('input_hash', sa.String(length=128), nullable=True),
        sa.Column('output_hash', sa.String(length=128), nullable=True),
        sa.Column('receipt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['commercial_agent_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_agent_executions_parent_execution_id'), 'commercial_agent_executions', ['parent_execution_id'], unique=False)
    op.create_index(op.f('ix_commercial_agent_executions_session_id'), 'commercial_agent_executions', ['session_id'], unique=False)

    # 3. CommercialAgentDelegationPolicy
    op.create_table(
        'commercial_agent_delegation_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_allowed', sa.Boolean(), nullable=True),
        sa.Column('constraints_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_agent_id'], ['commercial_agent_profiles.id'], ),
        sa.ForeignKeyConstraint(['target_agent_id'], ['commercial_agent_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. CommercialAgentToolExecution
    op.create_table(
        'commercial_agent_tool_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tool_name', sa.String(length=128), nullable=False),
        sa.Column('input_hash', sa.String(length=128), nullable=True),
        sa.Column('output_hash', sa.String(length=128), nullable=True),
        sa.Column('approval_status', sa.String(length=32), nullable=True),
        sa.Column('is_confidential', sa.Boolean(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['commercial_agent_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. CommercialAgentMemoryBoundary
    op.create_table(
        'commercial_agent_memory_boundaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('boundary_type', sa.String(length=32), nullable=True),
        sa.Column('access_log_hash', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['commercial_agent_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_agent_memory_boundaries_tenant_id'), 'commercial_agent_memory_boundaries', ['tenant_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_commercial_agent_memory_boundaries_tenant_id'), table_name='commercial_agent_memory_boundaries')
    op.drop_table('commercial_agent_memory_boundaries')
    op.drop_table('commercial_agent_tool_executions')
    op.drop_table('commercial_agent_delegation_policies')
    op.drop_index(op.f('ix_commercial_agent_executions_session_id'), table_name='commercial_agent_executions')
    op.drop_index(op.f('ix_commercial_agent_executions_parent_execution_id'), table_name='commercial_agent_executions')
    op.drop_table('commercial_agent_executions')
    op.drop_index(op.f('ix_commercial_agent_profiles_client_id'), table_name='commercial_agent_profiles')
    op.drop_table('commercial_agent_profiles')
