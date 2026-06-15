import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.llm_harness.providers import create_code_agent


@pytest.mark.asyncio
async def test_openrouter_provider_with_reasoning_content(monkeypatch):
    """Test OpenRouter provider with reasoning content enabled."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-test",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
            "stream": False,
            "supports_tool_calling": False,
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"type":"final","payload":{"message":"The word strawberry has 3 r\'s."}}'
                    ),
                    "reasoning_content": (
                        "Let me think about this... The word 'strawberry' has 3 r's."
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30},
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        response = await agent.chat_completion(
            [{"role": "user", "content": "How many r's are in the word strawberry?"}]
        )

    assert "choices" in response
    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"
    assert "3 r's" in content["message"]
    assert response["usage"]["total_tokens"] == 50
    assert "_provider_meta" in response
    assert "reasoning_content" in response["_provider_meta"]


@pytest.mark.asyncio
async def test_openrouter_provider_plain_chat_mode(monkeypatch):
    """Test OpenRouter provider in plain chat mode (no action validation)."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-chat",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
            "stream": False,
            "plain_chat": True,
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "The word 'strawberry' contains 3 r's.",
                }
            }
        ],
        "usage": {"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30},
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        response = await agent.chat_completion(
            [{"role": "user", "content": "How many r's are in the word strawberry?"}]
        )

    assert response["choices"][0]["message"]["content"] == "The word 'strawberry' contains 3 r's."
    assert response["usage"]["total_tokens"] == 50


@pytest.mark.asyncio
async def test_openrouter_provider_health_check(monkeypatch):
    """Test OpenRouter provider health check."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-health",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free"},
            {"id": "other-model"},
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        health = await agent.health_check()

    assert health["status"] == "healthy"
    assert health["provider"] == "openai-compatible"
    assert "nvidia/nemotron-3-ultra-550b-a55b:free" in health["details"]["available_models"]


@pytest.mark.asyncio
async def test_openrouter_provider_missing_api_key_fails():
    """Test that missing API key fails validation."""
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-no-key",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "NONEXISTENT_KEY",
        },
    )
    with pytest.raises(ValueError, match="API key not found"):
        await agent.health_check()


@pytest.mark.asyncio
async def test_openrouter_provider_model_not_found_suggests_alternatives(monkeypatch):
    """Test that missing model suggests alternatives."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-wrong-model",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/wrong-model",
            "api_key_env": "OPENROUTER_API_KEY",
        },
    )

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {
        "data": [
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free"},
            {"id": "other-model"},
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_models_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        health = await agent.health_check()
        assert health["status"] == "unhealthy"
        assert "nvidia/wrong-model" in health["error"]


@pytest.mark.asyncio
async def test_openrouter_provider_streaming_with_reasoning(monkeypatch):
    """Test OpenRouter provider with streaming and reasoning content."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-stream",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
            "stream": True,
            "plain_chat": True,
        },
    )

    class FakeStreamResponse:
        def raise_for_status(self):
            pass

        async def aiter_lines(self):
            for line in [
                'data: {"choices":[{"delta":{"reasoning_content":"Let me think..."}}]}',
                "",
                'data: {"choices":[{"delta":{"reasoning_content":" The answer is 3."}}]}',
                "",
                'data: {"choices":[{"delta":{"content":"The word strawberry has 3 r\'s."}}]}',
                "",
                "data: [DONE]",
                "",
            ]:
                yield line

    class FakeStreamContext:
        async def __aenter__(self):
            return FakeStreamResponse()

        async def __aexit__(self, *args):
            pass

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_inner_client = MagicMock()
        mock_inner_client.stream = MagicMock(return_value=FakeStreamContext())
        mock_inner_client.__aenter__ = AsyncMock(return_value=mock_inner_client)
        mock_inner_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_inner_client

        response = await agent.chat_completion(
            [{"role": "user", "content": "How many r's are in the word strawberry?"}]
        )

    assert "choices" in response
    assert "3 r's" in response["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_openrouter_provider_reasoning_only_response(monkeypatch):
    """Test OpenRouter provider when only reasoning_content is returned (no content)."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-reasoning-only",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
            "stream": False,
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": (
                        '{"type":"final","payload":{"message":"The word strawberry has 3 r\'s."}}'
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30},
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        response = await agent.chat_completion(
            [{"role": "user", "content": "How many r's are in the word strawberry?"}]
        )

    assert "choices" in response
    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"
    assert "3 r's" in content["message"]


@pytest.mark.asyncio
async def test_openrouter_provider_headers_correct(monkeypatch):
    """Test that OpenRouter provider sends correct headers."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-headers",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
        },
    )

    headers = agent._build_headers()
    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"] == "Bearer sk-or-v1-test"


@pytest.mark.asyncio
async def test_openrouter_provider_temperature_zero(monkeypatch):
    """Test that OpenRouter provider sends temperature=0."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "openrouter-temp",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "api_key_env": "OPENROUTER_API_KEY",
        },
    )

    sent_payloads = []

    async def capture_request(method, url, **kwargs):
        sent_payloads.append(kwargs.get("json", {}))
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type":"final","payload":{"message":"done"}}',
                    }
                }
            ],
            "usage": {"total_tokens": 10},
        }
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = capture_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert sent_payloads[0].get("temperature") == 0
