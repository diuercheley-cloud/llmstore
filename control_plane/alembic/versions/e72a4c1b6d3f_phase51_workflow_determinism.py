"""phase51_workflow_determinism

Revision ID: e72a4c1b6d3f
Revises: d91c7b2e3f4a
Create Date: 2026-05-15 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e72a4c1b6d3f'
down_revision = 'd91c7b2e3f4a'
branch_labels = None
depends_on = None


def upgrade():
    # 1. CommercialWorkflowDefinition
    op.create_table(
        'commercial_workflow_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_name', sa.String(length=128), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('steps_config', sa.JSON(), nullable=False),
        sa.Column('is_deterministic', sa.Boolean(), nullable=True),
        sa.Column('enforce_reproducibility', sa.Boolean(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_workflow_definitions_client_id'), 'commercial_workflow_definitions', ['client_id'], unique=False)

    # 2. CommercialWorkflowExecution
    op.create_table(
        'commercial_workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('definition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('execution_hash_chain', sa.String(length=128), nullable=True),
        sa.Column('current_step_index', sa.Integer(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['definition_id'], ['commercial_workflow_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_workflow_executions_session_id'), 'commercial_workflow_executions', ['session_id'], unique=False)

    # 3. CommercialWorkflowCheckpoint
    op.create_table(
        'commercial_workflow_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('step_input_hash', sa.String(length=128), nullable=True),
        sa.Column('step_output_hash', sa.String(length=128), nullable=True),
        sa.Column('state_snapshot', sa.JSON(), nullable=True),
        sa.Column('merkle_root', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['commercial_workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. CommercialWorkflowReplay
    op.create_table(
        'commercial_workflow_replays',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('replay_execution_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('mismatched_step_index', sa.Integer(), nullable=True),
        sa.Column('replay_report', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['original_execution_id'], ['commercial_workflow_executions.id'], ),
        sa.ForeignKeyConstraint(['replay_execution_id'], ['commercial_workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. CommercialWorkflowDeterminismReport
    op.create_table(
        'commercial_workflow_determinism_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('determinism_score', sa.Float(), nullable=True),
        sa.Column('drift_detected', sa.Boolean(), nullable=True),
        sa.Column('drift_summary', sa.Text(), nullable=True),
        sa.Column('verification_proof_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['commercial_workflow_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('commercial_workflow_determinism_reports')
    op.drop_table('commercial_workflow_replays')
    op.drop_table('commercial_workflow_checkpoints')
    op.drop_index(op.f('ix_commercial_workflow_executions_session_id'), table_name='commercial_workflow_executions')
    op.drop_table('commercial_workflow_executions')
    op.drop_index(op.f('ix_commercial_workflow_definitions_client_id'), table_name='commercial_workflow_definitions')
    op.drop_table('commercial_workflow_definitions')
