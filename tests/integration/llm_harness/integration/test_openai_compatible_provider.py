import asyncio
import json

import httpx
import pytest

from scripts.llm_harness.providers import OpenAICompatibleProvider


@pytest.fixture
def base_config():
    return {
        "agent_id": "test-agent",
        "base_url": "http://openai-mock/v1",
        "model": "gpt-4",
        "api_key_env": "MOCK_OPENAI_API_KEY",
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_compatible_chat_completion_valid_json(base_config, monkeypatch):
    monkeypatch.setenv("MOCK_OPENAI_API_KEY", "sk-valid-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == "Bearer sk-valid-key"
        resp_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type": "plan", "reason": "valid action", "payload": {"message": "planning", "reason": "valid action"}}',
                    }
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
        }
        return httpx.Response(200, json=resp_data)

    config = {**base_config, "transport": httpx.MockTransport(handler)}
    provider = OpenAICompatibleProvider(config)
    messages = [{"role": "user", "content": "Hello"}]
    response = await provider.chat_completion(messages)

    assert "choices" in response
    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "plan"
    assert content["reason"] == "valid action"
    assert content["message"] == "planning"
    assert response["usage"]["total_tokens"] == 40


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_compatible_chat_completion_invalid_json(base_config, monkeypatch):
    monkeypatch.setenv("MOCK_OPENAI_API_KEY", "sk-valid-key")

    def handler(request: httpx.Request) -> httpx.Response:
        resp_data = {
            "choices": [{"message": {"role": "assistant", "content": "Not a JSON at all!"}}]
        }
        return httpx.Response(200, json=resp_data)

    config = {**base_config, "transport": httpx.MockTransport(handler)}
    provider = OpenAICompatibleProvider(config)
    messages = [{"role": "user", "content": "Hello"}]

    with pytest.raises(ValueError, match="invalid_json"):
        await provider.chat_completion(messages)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_compatible_chat_completion_retry_on_503(base_config, monkeypatch):
    monkeypatch.setenv("MOCK_OPENAI_API_KEY", "sk-valid-key")
    attempts = 0

    async def async_noop(*args, **kwargs):
        pass

    monkeypatch.setattr(asyncio, "sleep", async_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="Service Unavailable")

        resp_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type": "final", "reason": "success", "payload": {"message": "ok"}}',
                    }
                }
            ]
        }
        return httpx.Response(200, json=resp_data)

    config = {**base_config, "max_retries": 2, "transport": httpx.MockTransport(handler)}
    provider = OpenAICompatibleProvider(config)

    messages = [{"role": "user", "content": "Hello"}]
    response = await provider.chat_completion(messages)

    assert response is not None
    assert attempts == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_compatible_chat_completion_no_retry_on_401(base_config, monkeypatch):
    monkeypatch.setenv("MOCK_OPENAI_API_KEY", "sk-invalid-key")
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, text="Unauthorized")

    config = {**base_config, "max_retries": 3, "transport": httpx.MockTransport(handler)}
    provider = OpenAICompatibleProvider(config)

    messages = [{"role": "user", "content": "Hello"}]
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await provider.chat_completion(messages)

    assert exc_info.value.response.status_code == 401
    assert attempts == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_compatible_streaming(base_config, monkeypatch):
    monkeypatch.setenv("MOCK_OPENAI_API_KEY", "sk-valid-key")

    def handler(request: httpx.Request) -> httpx.Response:
        # OpenAI streaming response is sent as SSE
        sse_lines = (
            'data: {"choices": [{"delta": {"role": "assistant"}}]}\n\n'
            'data: {"choices": [{"delta": {"content": "{\\"type\\": \\"final\\", "}}]}\n\n'
            'data: {"choices": [{"delta": {"content": "\\"reason\\": \\"stream\\", \\"payload\\": {\\"message\\": \\"streamed\\"}}"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(200, text=sse_lines)

    config = {**base_config, "stream": True, "transport": httpx.MockTransport(handler)}
    provider = OpenAICompatibleProvider(config)
    messages = [{"role": "user", "content": "Hello"}]
    response = await provider.chat_completion(messages)

    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"
    assert content["reason"] == "stream"
    assert content["message"] == "streamed"
