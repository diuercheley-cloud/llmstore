"""remediation execution governance

Revision ID: 003_remediation_governance
Revises: 002_token_tracking
Create Date: 2026-06-12 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_remediation_governance'
down_revision = '002_token_tracking'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # RemediationExecution updates
    op.add_column('remediation_executions', sa.Column('requested_by', sa.String(length=128), nullable=False, server_default='system'))
    op.add_column('remediation_executions', sa.Column('approved_by', sa.String(length=128), nullable=True))
    op.add_column('remediation_executions', sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('remediation_executions', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.add_column('remediation_executions', sa.Column('error_code', sa.String(length=100), nullable=True))
    op.add_column('remediation_executions', sa.Column('error_message', sa.String(length=1000), nullable=True))
    op.add_column('remediation_executions', sa.Column('correlation_id', sa.String(length=255), nullable=True))
    
    op.create_index(op.f('ix_remediation_executions_idempotency_key'), 'remediation_executions', ['idempotency_key'], unique=True)

    # RemediationExecutionStep updates
    op.add_column('remediation_execution_steps', sa.Column('output_summary', sa.String(length=1000), nullable=True))
    op.add_column('remediation_execution_steps', sa.Column('error_code', sa.String(length=100), nullable=True))
    op.add_column('remediation_execution_steps', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('remediation_execution_steps', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('remediation_execution_steps', 'completed_at')
    op.drop_column('remediation_execution_steps', 'started_at')
    op.drop_column('remediation_execution_steps', 'error_code')
    op.drop_column('remediation_execution_steps', 'output_summary')

    op.drop_index(op.f('ix_remediation_executions_idempotency_key'), table_name='remediation_executions')
    op.drop_column('remediation_executions', 'correlation_id')
    op.drop_column('remediation_executions', 'error_message')
    op.drop_column('remediation_executions', 'error_code')
    op.drop_column('remediation_executions', 'idempotency_key')
    op.drop_column('remediation_executions', 'current_step')
    op.drop_column('remediation_executions', 'approved_by')
    op.drop_column('remediation_executions', 'requested_by')
