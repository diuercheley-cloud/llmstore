"""agent optimization tables

Revision ID: phase93_agent_optimization
Revises: phase92_agent_iam
Create Date: 2026-05-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'phase93_agent_optimization'
down_revision: Union[str, Sequence[str], None] = 'phase92_agent_iam'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agent_optimization import (
        AgentOptimizationCandidate,
        AgentOptimizationExperiment,
        AgentOptimizationResult,
        AgentPolicyCandidate,
        AgentPromptCandidate,
        AgentToolSelectionCandidate,
    )
    bind = op.get_bind()
    tables = [
        AgentOptimizationExperiment.__table__,
        AgentOptimizationCandidate.__table__,
        AgentOptimizationResult.__table__,
        AgentPromptCandidate.__table__,
        AgentPolicyCandidate.__table__,
        AgentToolSelectionCandidate.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_tool_selection_candidates')
    op.drop_table('agent_policy_candidates')
    op.drop_table('agent_prompt_candidates')
    op.drop_table('agent_optimization_results')
    op.drop_table('agent_optimization_candidates')
    op.drop_table('agent_optimization_experiments')
