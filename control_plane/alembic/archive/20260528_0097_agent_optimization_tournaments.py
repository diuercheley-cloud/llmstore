"""agent optimization tournament tables

Revision ID: 20260528_0097
Revises: 20260528_0096
Create Date: 2026-05-28 15:05:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260528_0097"
down_revision: Union[str, Sequence[str], None] = "20260528_0096"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agents.agent_optimization_tournament import (
        AgentOptimizationPairwiseResult,
        AgentOptimizationTournament,
        AgentOptimizationTournamentCandidate,
        AgentOptimizationTournamentResult,
    )

    bind = op.get_bind()
    tables = [
        AgentOptimizationTournament.__table__,
        AgentOptimizationTournamentCandidate.__table__,
        AgentOptimizationTournamentResult.__table__,
        AgentOptimizationPairwiseResult.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table("agent_optimization_pairwise_results")
    op.drop_table("agent_optimization_tournament_results")
    op.drop_table("agent_optimization_tournament_candidates")
    op.drop_table("agent_optimization_tournaments")
