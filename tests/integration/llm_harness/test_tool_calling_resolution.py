import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from scripts.llm_harness.providers import create_code_agent, _PROBE_CACHE
import time

@pytest.mark.asyncio
async def test_resolve_mode_json_forced():
    agent = create_code_agent("local-openai-compatible", {
        "agent_id": "test",
        "tool_calling": "json"
    })
    mode = await agent.resolve_tool_calling_mode()
    assert mode == "json"

@pytest.mark.asyncio
async def test_resolve_mode_native_forced_unsupported_fails():
    agent = create_code_agent("local-openai-compatible", {
        "agent_id": "test",
        "tool_calling": "native",
        "base_url": "http://fake/v1"
    })
    
    async def fake_request(method, url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(ValueError, match="Native tool-calling requested but unsupported"):
            await agent.resolve_tool_calling_mode()

@pytest.mark.asyncio
async def test_resolve_mode_auto_local_defaults_to_json():
    agent = create_code_agent("local-openai-compatible", {
        "agent_id": "test",
        "tool_calling": "auto",
        "base_url": "http://fake/v1"
    })
    # Even if probe succeeds, it should default to JSON if allow_native_tools_for_local=False
    mock_probe_ok = {
        "choices": [{"message": {"tool_calls": [{"id": "c1", "type": "function", "function": {"name": "final", "arguments": "{}"}}]}}]
    }
    
    async def fake_request(method, url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_probe_ok
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mode = await agent.resolve_tool_calling_mode()
        assert mode == "json"

@pytest.mark.asyncio
async def test_resolve_mode_auto_local_with_allow_uses_native():
    agent = create_code_agent("local-openai-compatible", {
        "agent_id": "test",
        "tool_calling": "auto",
        "base_url": "http://fake/v1",
        "allow_native_tools_for_local": True
    })
    mock_probe_ok = {
        "choices": [{"message": {"tool_calls": [{"id": "c1", "type": "function", "function": {"name": "final", "arguments": "{}"}}]}}]
    }
    
    async def fake_request(method, url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_probe_ok
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mode = await agent.resolve_tool_calling_mode()
        assert mode == "native"

@pytest.mark.asyncio
async def test_probe_cache_works():
    _PROBE_CACHE.clear()
    agent = create_code_agent("local-openai-compatible", {
        "agent_id": "test",
        "base_url": "http://fake/v1",
        "model": "m1",
        "allow_native_tools_for_local": True
    })
    
    mock_probe_ok = {
        "choices": [{"message": {"tool_calls": [{"id": "c1", "type": "function", "function": {"name": "final", "arguments": "{}"}}]}}]
    }
    
    call_count = 0
    async def fake_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_probe_ok
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # First call
        probe1 = await agent._probe_native_tool_calling()
        assert probe1["supported"] is True
        assert probe1.get("capability_probe_cache_hit") is False
        assert call_count == 1
        
        # Second call should be cached
        probe2 = await agent._probe_native_tool_calling()
        assert probe2["supported"] is True
        assert probe2.get("capability_probe_cache_hit") is True
        assert call_count == 1
