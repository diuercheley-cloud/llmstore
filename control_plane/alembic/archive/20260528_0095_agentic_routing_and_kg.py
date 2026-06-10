"""agentic routing and knowledge graph tables

Revision ID: 20260528_0095
Revises: 20260527_0094
Create Date: 2026-05-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260528_0095'
down_revision: Union[str, Sequence[str], None] = '20260527_0094'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agents.agent_knowledge_graph import (
        AgentKGEntity,
        AgentKGEntitySource,
        AgentKGExtractionRun,
        AgentKGQueryEvent,
        AgentKGRelation,
        AgentKGSource,
    )
    from app.models.agents.agent_routing import (
        AgentCostQualityProfile,
        AgentModelCapability,
        AgentRoutingPolicy,
        AgentStepRoutingDecision,
    )
    bind = op.get_bind()
    tables = [
        AgentModelCapability.__table__,
        AgentRoutingPolicy.__table__,
        AgentCostQualityProfile.__table__,
        AgentStepRoutingDecision.__table__,
        AgentKGEntity.__table__,
        AgentKGSource.__table__,
        AgentKGEntitySource.__table__,
        AgentKGRelation.__table__,
        AgentKGExtractionRun.__table__,
        AgentKGQueryEvent.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_kg_query_events')
    op.drop_table('agent_kg_extraction_runs')
    op.drop_table('agent_kg_relations')
    op.drop_table('agent_kg_entity_sources')
    op.drop_table('agent_kg_sources')
    op.drop_table('agent_kg_entities')
    op.drop_table('agent_step_routing_decisions')
    op.drop_table('agent_cost_quality_profiles')
    op.drop_table('agent_routing_policies')
    op.drop_table('agent_model_capabilities')
