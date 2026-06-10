import uuid

import pytest
from app.models.agents.agent_deployments import AgentApiDeployment
from app.models.agents.agents import AgentDefinition
from app.services.agent_deployments.agent_api_deployment import (
    AgentApiDeploymentService,
    DeploymentValidationError,
)
from app.services.agent_deployments.agent_endpoint_registry import AgentEndpointRegistry
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_agent_deployment_lifecycle(session: AsyncSession):
    svc = AgentApiDeploymentService(session)
    tenant_id = "test-tenant"
    
    # 1. Setup: Create approved agent
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Deployable Agent",
        version="1.0.0",
        tenant_id=tenant_id,
        status="active",
        instructions="Hello",
        model_id="gpt-4",
        owner="test"
    )
    session.add(agent)
    await session.flush()
    
    # 2. Deploy agent
    deployment = await svc.create_deployment(
        tenant_id=tenant_id,
        agent_id=agent.id,
        slug="test-agent-api",
        name="Test API"
    )
    assert deployment.id is not None
    assert deployment.slug == "test-agent-api"
    assert deployment.status == "active"
    
    # 3. Validation: Cannot deploy draft
    draft_agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Draft Agent",
        version="1.0.0",
        tenant_id=tenant_id,
        status="draft",
        instructions="Hi",
        model_id="gpt-4",
        owner="test"
    )
    session.add(draft_agent)
    await session.flush()
    
    with pytest.raises(DeploymentValidationError) as exc:
        await svc.create_deployment(tenant_id, draft_agent.id, "draft-api", "Draft")
    assert "must be active or approved" in str(exc.value)

@pytest.mark.asyncio
async def test_deployment_invocation(session: AsyncSession):
    from app.core.config import get_settings
    settings = get_settings()
    settings.agent_runtime_enabled = True
    settings.agent_execution_plane_enabled = True
    
    svc = AgentApiDeploymentService(session)
    tenant_id = "test-tenant"
    
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="Executable Agent",
        version="1.0.0",
        tenant_id=tenant_id,
        status="active",
        instructions="Echo: {{ input }}",
        model_id="gpt-4",
        owner="test"
    )
    session.add(agent)
    await session.flush()
    
    deployment = await svc.create_deployment(tenant_id, agent.id, "invoke-api", "Invoke API")
    await session.commit()
    
    registry = AgentEndpointRegistry(session)
    
    # 1. Async Invoke
    resp = await registry.invoke_async(deployment, "Test input", tenant_id)
    assert "run_id" in resp
    run_id = uuid.UUID(resp["run_id"])
    
    # 2. Sync Invoke (with short timeout to test timeout logic if it were slow)
    # Since we use mock LLM it should be fast
    resp_sync = await registry.invoke_sync(deployment, "Sync input", tenant_id, timeout_seconds=5)
    assert "run_id" in resp_sync
    assert resp_sync["status"] in ("completed", "running", "queued")

@pytest.mark.asyncio
async def test_rate_limiting(session: AsyncSession):
    from app.services.agent_deployments.deployment_router import deployment_router
    
    deployment = AgentApiDeployment(
        id=uuid.uuid4(),
        tenant_id="test",
        agent_id=uuid.uuid4(),
        slug="rate-limited",
        name="Limited",
        rate_limit_per_minute=1 # Only 1 per minute
    )
    
    # First one allowed
    assert deployment_router.check_rate_limit(deployment) is True
    # Second one blocked
    assert deployment_router.check_rate_limit(deployment) is False

@pytest.mark.asyncio
async def test_rollback_deployment(session: AsyncSession):
    svc = AgentApiDeploymentService(session)
    tenant_id = "test-tenant"
    
    agent_v1 = AgentDefinition(id=uuid.uuid4(), name="Agent V1", version="1.0.0", tenant_id=tenant_id, status="active", instructions="V1", model_id="gpt-4", owner="test")
    agent_v2 = AgentDefinition(id=uuid.uuid4(), name="Agent V2", version="2.0.0", tenant_id=tenant_id, status="active", instructions="V2", model_id="gpt-4", owner="test")
    session.add_all([agent_v1, agent_v2])
    await session.flush()
    
    dep_v1 = await svc.create_deployment(tenant_id, agent_v1.id, "api-v1", "API V1")
    dep_v2 = await svc.create_deployment(tenant_id, agent_v2.id, "api-v2", "API V2")
    await session.commit()
    
    # Rollback dep_v2 to v1 configuration
    rolled = await svc.rollback_deployment(dep_v2.id, tenant_id, "api-v1")
    assert str(rolled.agent_id) == str(agent_v1.id)
    assert rolled.previous_version_slug == "api-v2"
