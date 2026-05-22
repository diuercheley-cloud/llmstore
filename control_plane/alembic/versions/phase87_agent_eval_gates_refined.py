# Models: AgentEvalFailure
"""Agent Evals Operational Gates

Revision ID: phase87_agent_eval_gates_refined
Revises: phase86_agent_observability
Create Date: 2026-05-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'phase87_agent_eval_gates_refined'
down_revision: Union[str, None] = 'phase86_agent_observability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add is_golden to agent_eval_cases
    op.add_column('agent_eval_cases', sa.Column('is_golden', sa.Boolean(), server_default='false', nullable=False))

    # 2. agent_eval_failures
    op.create_table('agent_eval_failures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('failure_type', sa.String(length=64), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_failures_agent_id'), 'agent_eval_failures', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_eval_failures_run_id'), 'agent_eval_failures', ['run_id'], unique=False)

    # 3. Rename agent_promotion_gate_results to agent_eval_promotion_gates if it exists
    # Or just create it if it didn't exist in previous turns
    # In my previous turn I saw it existed.
    op.rename_table('agent_promotion_gate_results', 'agent_eval_promotion_gates')

def downgrade() -> None:
    op.rename_table('agent_eval_promotion_gates', 'agent_promotion_gate_results')
    op.drop_table('agent_eval_failures')
    op.drop_column('agent_eval_cases', 'is_golden')
