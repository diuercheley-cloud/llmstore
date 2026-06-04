import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import get_settings
from app.models.agents import AgentDefinition, AgentRun
from app.models.client import Client
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.agents.agent_llm_provider import GatewayAgentLLMProvider, ProviderUnavailableError
from app.services.inference_proxy import ForwardResult, InferenceProxy
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse


@pytest.mark.asyncio
async def test_gateway_llm_provider_success(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_REAL_LLM_ENABLED", "true")
    get_settings.cache_clear()

    # 1. Setup mock data
    tenant_id = str(uuid.uuid4())
    client = Client(
        id=uuid.UUID(tenant_id), 
        name="Test Client",
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=20000,
        rate_limit_per_minute=100,
        max_output_tokens=1000,
        max_context_tokens=4096
    )
    session.add(client)
    
    model = ModelRegistry(
        model_id="gpt-4",
        model_file="gpt4.bin",
        provider="openai",
        status="active"
    )
    session.add(model)
    
    backend = InferenceBackend(
        name="openai-backend",
        provider="openai",
        backend_url="https://api.openai.com",
        status="active"
    )
    session.add(backend)
    await session.flush()
    
    route = ModelBackendRoute(
        model_registry_id=model.id,
        inference_backend_id=backend.id,
        priority=1,
    )
    session.add(route)
    
    agent_def = AgentDefinition(
        name="Test Agent",
        version="1.0.0",
        instructions="Be a helpful assistant.",
        model_id="gpt-4",
        owner="tester",
        tenant_id=tenant_id
    )
    session.add(agent_def)
    await session.flush()
    
    run = AgentRun(
        agent_id=agent_def.id,
        tenant_id=tenant_id,
        input_text="Hello",
        status="running"
    )
    session.add(run)
    await session.commit()
    await session.refresh(agent_def)
    await session.refresh(run)

    # 2. Mock InferenceProxy
    mock_proxy = MagicMock(spec=InferenceProxy)
    
    content = {
        "choices": [{"message": {"content": "Hello there!"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3}
    }
    mock_response = JSONResponse(content=content)
    
    forward_result = ForwardResult(
        response=mock_response,
        backend_name=backend.name,
        attempts=1,
        fallback_used=False,
        backend_errors=[]
    )
    mock_proxy.chat = AsyncMock(return_value=forward_result)

    # 3. Test Provider
    provider = GatewayAgentLLMProvider(session, mock_proxy)
    
    # Mock quota and billing to avoid deep logic
    with patch("app.services.agents.agent_llm_provider.ensure_quota", AsyncMock()), \
         patch("app.services.agents.agent_llm_provider.record_usage", AsyncMock()):
        
        result = await provider.generate(agent_def, run, allowed_tools=[])

    # 4. Assertions
    assert result["type"] == "final"
    assert result["output"] == "Hello there!"
    assert result["usage"]["prompt_tokens"] == 5
    assert result["backend_name"] == "openai-backend"
    
    # Verify proxy was called with correct payload
    mock_proxy.chat.assert_called_once()
    args, kwargs = mock_proxy.chat.call_args
    payload = kwargs["payload"]
    assert payload["model"] == "gpt-4"
    assert payload["messages"][0]["content"] == "Be a helpful assistant."
    assert payload["messages"][1]["content"] == "Hello"

@pytest.mark.asyncio
async def test_gateway_llm_provider_real_disabled(session: AsyncSession, monkeypatch):
    monkeypatch.setenv("AGENT_REAL_LLM_ENABLED", "false")
    get_settings.cache_clear()

    mock_proxy = MagicMock(spec=InferenceProxy)
    provider = GatewayAgentLLMProvider(session, mock_proxy)
    
    agent_def = MagicMock(spec=AgentDefinition)
    run = MagicMock(spec=AgentRun)
    
    with pytest.raises(ProviderUnavailableError) as exc:
        await provider.generate(agent_def, run, allowed_tools=[])
    assert "AGENT_REAL_LLM_ENABLED is false" in str(exc.value)
    mock_proxy.chat.assert_not_called()
