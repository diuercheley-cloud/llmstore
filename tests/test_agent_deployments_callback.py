import pytest
import uuid
import json
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_deployments.deployment_callback import DeploymentCallbackService
from app.models.agent_deployments import AgentApiDeployment, AgentApiUsageEvent
from app.models.agents import AgentRun

@pytest.mark.asyncio
async def test_trigger_callback_success(session: AsyncSession):
    # Setup
    deployment = AgentApiDeployment(
        id=uuid.uuid4(),
        tenant_id="test",
        agent_id=uuid.uuid4(),
        slug="test-slug",
        name="Test",
        callback_url="http://example.com/webhook",
        callback_secret="secret"
    )
    session.add(deployment)
    
    run = AgentRun(
        id=uuid.uuid4(),
        agent_id=deployment.agent_id,
        tenant_id="test",
        status="completed",
        input_text="Test input"
    )
    session.add(run)
    await session.flush()
    
    usage = AgentApiUsageEvent(
        id=uuid.uuid4(),
        deployment_id=deployment.id,
        run_id=run.id,
        client_id="test",
        tokens_used=10,
        estimated_cost_brl=0.01,
        created_at=run.created_at
    )
    session.add(usage)
    await session.commit()
    
    service = DeploymentCallbackService(session)
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        
        await service.trigger_callback(run.id)
        
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert args[0] == "http://example.com/webhook"
        payload = json.loads(kwargs["content"])
        assert payload["run_id"] == str(run.id)
        assert "X-Agent-Signature" in kwargs["headers"]

@pytest.mark.asyncio
async def test_trigger_callback_no_webhook(session: AsyncSession):
    deployment = AgentApiDeployment(
        id=uuid.uuid4(),
        tenant_id="test",
        agent_id=uuid.uuid4(),
        slug="no-hook",
        name="No Hook"
    )
    session.add(deployment)
    
    run = AgentRun(id=uuid.uuid4(), agent_id=deployment.agent_id, tenant_id="test")
    session.add(run)
    
    usage = AgentApiUsageEvent(deployment_id=deployment.id, run_id=run.id, client_id="test", tokens_used=0, estimated_cost_brl=0, created_at=run.created_at)
    session.add(usage)
    await session.commit()
    
    service = DeploymentCallbackService(session)
    with patch("httpx.AsyncClient.post") as mock_post:
        await service.trigger_callback(run.id)
        assert not mock_post.called
