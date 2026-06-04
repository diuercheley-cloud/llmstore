# Owner: agent-platform
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.agents import AgentRun
from app.models.multi_agent import AgentTeam, AgentTeamMember
from app.services.agents.multi_agent.hierarchical_runtime import HierarchicalRuntime
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_hierarchical_real_delegation(mock_db):
    runtime = HierarchicalRuntime(mock_db)
    team_id = uuid.uuid4()
    tenant_id = "tenant_123"
    
    # Setup team and members
    team = AgentTeam(id=team_id, tenant_id=tenant_id, topology="hierarchical")
    manager = AgentTeamMember(agent_id=uuid.uuid4(), role="manager")
    specialist = AgentTeamMember(agent_id=uuid.uuid4(), role="specialist")
    
    # Mock data retrieval
    runtime.get_team = AsyncMock(return_value=team)
    runtime.get_members = AsyncMock(return_value=[manager, specialist])
    
    # Mock run creation
    parent_run = AgentRun(id=uuid.uuid4(), agent_id=manager.agent_id, tenant_id=tenant_id, status="running")
    runtime.start_run = AsyncMock(return_value=parent_run)
    
    # Mock workspace and observability
    runtime.get_workspace = MagicMock()
    runtime.obs = MagicMock()
    runtime.arbitrator = MagicMock()
    runtime.arbitrator.arbitrate = AsyncMock(return_value={"final_synthesis": "done", "consensus": True, "confidence_score": 0.9})
    runtime.complete_run = AsyncMock()

    # REAL DELEGATION MOCK
    sub_run = AgentRun(id=uuid.uuid4(), agent_id=specialist.agent_id, status="completed", estimated_cost_brl=0.01)
    
    with pytest.MonkeyPatch().context() as m:
        mock_start_run = AsyncMock(return_value=sub_run)
        m.setattr("app.services.agents.agent_runtime.start_run", mock_start_run)
        
        await runtime.execute(team_id, "Find secrets")
        
        # Verify real delegation occurred
        mock_start_run.assert_called()
        args, kwargs = mock_start_run.call_args
        assert kwargs["parent_run_id"] == parent_run.id
        assert kwargs["agent_id"] == specialist.agent_id
