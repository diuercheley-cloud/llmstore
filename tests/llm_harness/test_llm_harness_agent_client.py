import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scripts.llm_harness.agent_client import AgentClient
from scripts.llm_harness.models import ExecutionResult
from scripts.llm_harness.reporter import Reporter


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data
        self.text = text or json.dumps(data or {})

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("Error", request=MagicMock(), response=self)

    def json(self):
        return self._data


class FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-key")


@pytest.mark.asyncio
async def test_agent_client_openai_compatible_http_call(mock_env):
    mock_client = AsyncMock()
    mock_client.request.return_value = FakeResponse(
        data={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type":"final","payload":{"message":"ok"}}',
                    }
                }
            ]
        }
    )
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("scripts.llm_harness.providers.httpx.AsyncClient", return_value=mock_client):
        client = AgentClient(
            agent_id="test",
            base_url="http://localhost:8000",
            provider="openai-compatible",
            model="test-model",
        )
        response = await client.chat_completion(messages=[{"role": "user", "content": "hi"}])

    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"
    assert content["message"] == "ok"
    mock_client.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_client_retry_503(mock_env):
    mock_client = AsyncMock()
    mock_client.request.side_effect = [
        FakeResponse(503),
        FakeResponse(
            200,
            data={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"type":"plan","payload":{"reason":"next"}}'
                            )
                        }
                    }
                ]
            },
        ),
    ]
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "scripts.llm_harness.providers.httpx.AsyncClient",
        return_value=mock_client,
    ), patch("asyncio.sleep", new_callable=AsyncMock):
        client = AgentClient(
            agent_id="test",
            base_url="http://localhost:8000",
            provider="openai-compatible",
            model="test-model",
            max_retries=1,
        )
        response = await client.chat_completion(messages=[{"role": "user", "content": "go"}])

    assert mock_client.request.call_count == 2
    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "plan"


@pytest.mark.asyncio
async def test_agent_client_no_retry_401(mock_env):
    mock_client = AsyncMock()
    mock_client.request.side_effect = [FakeResponse(401, text="Unauthorized")]
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("scripts.llm_harness.providers.httpx.AsyncClient", return_value=mock_client):
        client = AgentClient(
            agent_id="test",
            base_url="http://localhost:8000",
            provider="openai-compatible",
            model="test-model",
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat_completion(messages=[{"role": "user", "content": "go"}])

    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_agent_client_control_plane_sse(mock_env):
    mock_client = AsyncMock()
    mock_client.request.side_effect = [
        FakeResponse(200, data=[{"id": "test", "name": "Test Agent", "status": "active"}]),
        FakeResponse(200, data={"id": "run-123"}),
    ]
    mock_client.stream = MagicMock(
        return_value=FakeStreamResponse(
            [
                "event: plan",
                'data: {"type":"plan","payload":{"message":"Planning","reason":"test"}}',
                "",
            ]
        )
    )
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("scripts.llm_harness.providers.httpx.AsyncClient", return_value=mock_client):
        client = AgentClient(
            agent_id="test",
            base_url="http://localhost:8000",
            provider="control-plane",
            model="test-model",
        )
        response = await client.chat_completion(messages=[{"role": "user", "content": "hi"}])

    content = json.loads(response["choices"][0]["message"]["content"])
    assert content["action_type"] == "plan"
    assert content["reason"] == "test"


@pytest.mark.asyncio
async def test_agent_client_invalid_json(mock_env):
    mock_client = AsyncMock()
    mock_client.request.return_value = FakeResponse(
        data={"choices": [{"message": {"content": "invalid json"}}]}
    )
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("scripts.llm_harness.providers.httpx.AsyncClient", return_value=mock_client):
        client = AgentClient(
            agent_id="test",
            base_url="http://localhost:8000",
            provider="openai-compatible",
            model="test-model",
        )
        with pytest.raises(ValueError, match="invalid_json"):
            await client.chat_completion(messages=[{"role": "user", "content": "go"}])


def test_agent_client_redaction(mock_env, tmp_path):
    client = AgentClient(
        agent_id="test",
        base_url="http://localhost:8000",
        provider="openai-compatible",
        model="test-model",
    )
    headers = client._build_headers()
    assert headers["Authorization"] == "Bearer test-secret-key"

    assert "test-secret-key" not in repr(client)
    sanitized = client._sanitize_log_headers(headers)
    assert sanitized["Authorization"] == "Bearer [REDACTED]"

    reporter = Reporter(output_dir=str(tmp_path))
    result = ExecutionResult(
        success=False,
        error="Authorization: Bearer test-secret-key api_key=test-secret-key",
    )
    filename = reporter.generate_summary(
        result,
        trace=[],
        policy_info={"provider": "openai-compatible"},
    )
    report_content = (tmp_path / filename).read_text()
    assert "test-secret-key" not in report_content


@pytest.mark.asyncio
async def test_agent_client_usage_propagates(mock_env):
    """Verify usage from provider response propagates through AgentClient."""
    mock_client = AsyncMock()
    mock_client.request.return_value = FakeResponse(
        data={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type":"final","payload":{"message":"ok"}}',
                    }
                }
            ],
            "usage": {"total_tokens": 75, "prompt_tokens": 25, "completion_tokens": 50},
        }
    )
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("scripts.llm_harness.providers.httpx.AsyncClient", return_value=mock_client):
        client = AgentClient(
            agent_id="test",
            base_url="http://localhost:8000",
            provider="openai-compatible",
            model="test-model",
        )
        response = await client.chat_completion(messages=[{"role": "user", "content": "hi"}])

    assert response["usage"]["total_tokens"] == 75
    assert response["usage"]["prompt_tokens"] == 25
    assert response["usage"]["completion_tokens"] == 50


@pytest.mark.asyncio
async def test_agent_client_config():
    client = AgentClient(agent_id="test-agent")
    config = await client.get_agent_config()
    assert config["id"] == "test-agent"
    assert "capabilities" in config


@pytest.mark.asyncio
async def test_agent_client_chat():
    client = AgentClient(agent_id="test-agent")
    response = await client.chat_completion(messages=[{"role": "user", "content": "hi"}])
    assert "choices" in response
    assert response["choices"][0]["message"]["role"] == "assistant"
