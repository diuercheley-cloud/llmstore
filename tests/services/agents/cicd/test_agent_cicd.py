# Owner: agent-platform
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_cicd import AgentPipeline, AgentDeployment
from app.services.agents.cicd.agent_pipeline import AgentPipelineService
from app.services.agents.cicd.blue_green_deployment import BlueGreenDeploymentService
from app.services.agents.cicd.rollback_executor import RollbackExecutor
from app.services.agents.cicd.cicd_adapters import GitHubActionsAdapter

@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_pipeline_run_success(mock_db):
    service = AgentPipelineService(mock_db)
    pipeline_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    pipeline = AgentPipeline(id=pipeline_id, agent_id=agent_id, status="pending")
    
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: pipeline))
    
    # We need to mock _step_deploy to avoid importing BlueGreenDeploymentService inside test
    service._step_deploy = AsyncMock()
    
    await service.run_pipeline(pipeline_id)
    assert pipeline.status == "completed"

@pytest.mark.asyncio
async def test_blue_green_traffic_switch(mock_db):
    service = BlueGreenDeploymentService(mock_db)
    deployment_id = uuid.uuid4()
    deployment = AgentDeployment(id=deployment_id, traffic_weight=0.0)
    
    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: deployment))
    
    await service.switch_traffic(deployment_id, 0.5)
    assert deployment.traffic_weight == 0.5
    assert deployment.status == "in_progress"

    await service.switch_traffic(deployment_id, 1.0)
    assert deployment.status == "completed"

@pytest.mark.asyncio
async def test_rollback_execution(mock_db):
    executor = RollbackExecutor(mock_db)
    deployment_id = uuid.uuid4()
    deployment = AgentDeployment(id=deployment_id, agent_id=uuid.uuid4(), status="completed")
    
    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: deployment),
        MagicMock(scalar_one_or_none=lambda: MagicMock()) # registry entry
    ])
    
    success = await executor.execute_rollback(deployment_id, "Critical Error")
    assert success is True
    assert deployment.status == "rolled_back"

def test_github_workflow_generation():
    adapter = GitHubActionsAdapter()
    yaml_content = adapter.generate_workflow("agent_123", "tenant_abc")
    
    assert "name: Agent Deploy - agent_123" in yaml_content
    assert "agents/agent_123/**" in yaml_content
    assert "Trigger Agent Pipeline" in yaml_content
