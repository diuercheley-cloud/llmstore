# Owner: agent-platform
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentDefinition
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
    pipeline = AgentPipeline(
        id=pipeline_id,
        agent_id=agent_id,
        status="pending",
        tenant_id="tenant-a",
        config={"promotion_environments": ["staging"], "production_approved": True},
    )
    agent = AgentDefinition(
        id=agent_id,
        tenant_id="tenant-a",
        name="Test Agent",
        version="1.0.0",
        instructions="Run the deployment pipeline.",
        model_id="mock-model",
        owner="tests",
        allowed_tools=[],
    )
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=lambda: pipeline),
            MagicMock(scalar_one_or_none=lambda: agent),
            MagicMock(scalar_one_or_none=lambda: agent),
        ]
    )
    
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
async def test_progressive_rollout_marks_failed_when_health_fails(mock_db):
    service = BlueGreenDeploymentService(mock_db)
    deployment_id = uuid.uuid4()
    deployment = AgentDeployment(id=deployment_id, traffic_weight=0.0, status="in_progress")

    mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: deployment))

    success = await service.progressive_rollout(deployment_id, weights=[0.25], healthy=False)

    assert success is False
    assert deployment.status == "failed"

@pytest.mark.asyncio
async def test_rollback_execution(mock_db):
    executor = RollbackExecutor(mock_db)
    deployment_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    deployment = AgentDeployment(id=deployment_id, agent_id=agent_id, environment="production", version_tag="v2", status="completed")
    previous = AgentDeployment(id=uuid.uuid4(), agent_id=agent_id, environment="production", version_tag="v1", status="completed")
    registry = MagicMock(status="deprecated")
    
    mock_db.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=lambda: deployment),
        MagicMock(scalars=lambda: MagicMock(first=lambda: previous)),
        MagicMock(scalar_one_or_none=lambda: registry),
    ])
    
    success = await executor.execute_rollback(deployment_id, "Critical Error")
    assert success is True
    assert deployment.status == "rolled_back"
    assert registry.status == "active"


@pytest.mark.asyncio
async def test_pipeline_requires_production_approval(mock_db):
    service = AgentPipelineService(mock_db)
    pipeline = AgentPipeline(
        id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        tenant_id="tenant-a",
        status="pending",
        config={"promotion_environments": ["production"], "require_manual_approval_for_production": True, "production_approved": False},
    )

    with pytest.raises(RuntimeError, match="approval missing"):
        await service._step_deploy(pipeline, "production")

def test_github_workflow_generation():
    adapter = GitHubActionsAdapter()
    yaml_content = adapter.generate_workflow("agent_123", "tenant_abc")
    
    assert "name: Agent Deploy - agent_123" in yaml_content
    assert "agents/agent_123/**" in yaml_content
    assert "Trigger Agent Pipeline" in yaml_content
