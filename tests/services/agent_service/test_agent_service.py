# Owner: agent-platform
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_service import AgentServiceTier
from app.services.agent_service.agent_service_api import AgentServiceAPI
from app.services.agent_service.agent_rate_limits import AgentRateLimitService
from app.services.agent_service.sync_mode import SyncInvocationService

@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    service = AgentRateLimitService()
    tenant_id = "tenant_1"
    limit = 2
    
    # 1. Allow within limit
    assert await service.check_rate_limit(tenant_id, limit) is True
    assert await service.check_rate_limit(tenant_id, limit) is True
    
    # 2. Block beyond limit
    assert await service.check_rate_limit(tenant_id, limit) is False

@pytest.mark.asyncio
async def test_invoke_agent_sync_success(mock_db):
    api = AgentServiceAPI(mock_db)
    agent_id = uuid.uuid4()
    tenant_id = "tenant_1"
    run_id = uuid.uuid4()
    
    # Mock Tier and SyncInvoker
    tier = AgentServiceTier(id=uuid.uuid4(), name="pro", rate_limit_per_minute=10, features={"sync_mode": True})
    api.tiers.get_tier = AsyncMock(return_value=tier)
    
    api.sync_invoker.invoke_sync = AsyncMock(return_value={
        "run_id": str(run_id),
        "status": "completed",
        "output": "The answer is 42"
    })
    
    result = await api.invoke_agent(agent_id, tenant_id, "What is the answer?", mode="sync", tier_name="pro")
    
    assert result["status"] == "completed"
    assert result["output"] == "The answer is 42"
    api.sync_invoker.invoke_sync.assert_called_once()

@pytest.mark.asyncio
async def test_callback_registration(mock_db):
    from app.services.agent_service.callback_webhooks import CallbackWebhookService
    service = CallbackWebhookService(mock_db)
    agent_id = uuid.uuid4()
    
    webhook = await service.register_webhook(agent_id, "tenant_1", "https://hooks.example.com/callback")
    
    assert webhook.url == "https://hooks.example.com/callback"
    assert webhook.secret_key is not None
    assert webhook.is_active is True
