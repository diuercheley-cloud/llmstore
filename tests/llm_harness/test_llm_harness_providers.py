import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scripts.llm_harness.providers import create_code_agent


def test_provider_unknown_fails():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_code_agent("unknown", {"agent_id": "test"})


@pytest.mark.asyncio
async def test_provider_stub():
    agent = create_code_agent("stub", {"agent_id": "test"})
    res = await agent.chat_completion([])
    assert "choices" in res
    assert "final" in res["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_provider_openai_compatible(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
            "api_key_env": "OPENAI_API_KEY",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"type": "final", "payload": {"message": "done"}}',
                }
            }
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        res = await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert "choices" in res
    content = json.loads(res["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"


@pytest.mark.asyncio
async def test_provider_openai_auth_error_no_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
            "max_retries": 3,
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.request = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=mock_response.request, response=mock_response
    )

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await agent.chat_completion([{"role": "user", "content": "hi"}])

        # auth error 401/403 must fail immediately without retries
        assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_provider_openai_invalid_action(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "invalid json content",
                }
            }
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValueError, match="invalid_json"):
            await agent.chat_completion([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_provider_local_openai_compatible_no_key():
    # Local provider should not raise api key missing error on validation
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://localhost:11434",
            "model": "llama3",
            "api_key_env": "SOME_NONEXISTENT_KEY",
        },
    )
    assert agent.model == "llama3"


@pytest.mark.asyncio
async def test_provider_local_openai_auto_selects_model(monkeypatch):
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "stream": False,
        },
    )

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {
        "data": [
            {"id": "qwen/qwen3.6-35b-a3b"},
            {"id": "google/gemma-4-e2b"},
        ]
    }

    mock_chat_response = MagicMock()
    mock_chat_response.status_code = 200
    mock_chat_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"type": "final", "payload": {"message": "done"}}',
                }
            }
        ],
        "usage": {"total_tokens": 10},
    }

    requests = []

    async def fake_request(method, url, **kwargs):
        requests.append((method, url, kwargs.get("json")))
        mock_resp = mock_models_response if method == "GET" else mock_chat_response
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert agent.model == "qwen/qwen3.6-35b-a3b"
    assert result["choices"][0]["message"]["content"].startswith('{"action_type": "final"')
    assert any(req[0] == "GET" for req in requests)
    assert any(req[0] == "POST" for req in requests)


@pytest.mark.asyncio
async def test_provider_local_openai_health_reports_model_catalog(monkeypatch):
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
        },
    )

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {
        "data": [
            {"id": "qwen/qwen3.6-35b-a3b"},
            {"id": "google/gemma-4-e2b"},
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_models_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        health = await agent.health_check()

    assert health["status"] == "healthy"
    details = health["details"]
    assert details["selected_model"] == "qwen/qwen3.6-35b-a3b"
    assert details["available_models"] == ["qwen/qwen3.6-35b-a3b", "google/gemma-4-e2b"]
    assert details["auto_selected_model"] is True


@pytest.mark.asyncio
async def test_provider_local_openai_invalid_model_suggests_close_matches(monkeypatch):
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "qwen/qwen3.6-35b-wrong",
        },
    )

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {
        "data": [
            {"id": "qwen/qwen3.6-35b-a3b"},
            {"id": "google/gemma-4-e2b"},
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_models_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValueError, match="was not found"):
            await agent.chat_completion([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_provider_local_timeout_suggests_local_model_timeout():
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://localhost:1234/v1",
        },
    )

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        request = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")
        mock_client.request.side_effect = httpx.ReadTimeout("timed out", request=request)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.ReadTimeout, match="300s"):
            await agent._request_with_retry("POST", "http://localhost:1234/v1/chat/completions")


@pytest.mark.asyncio
async def test_provider_local_timeout_auto_increase_retries_once():
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://localhost:1234/v1",
            "auto_increase_timeout": True,
        },
    )
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.raise_for_status.return_value = None
    request = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.side_effect = [
            httpx.ReadTimeout("timed out", request=request),
            success_response,
        ]
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        response = await agent._request_with_retry("POST", "http://localhost:1234/v1/chat/completions")

    assert response is success_response
    assert agent.timeout_adjusted is True
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_provider_remote_timeout_does_not_auto_increase(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "https://api.example.com/v1",
            "model": "model-1",
            "auto_increase_timeout": True,
        },
    )

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
        mock_client.request.side_effect = httpx.ReadTimeout("timed out", request=request)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(httpx.ReadTimeout, match="Read timeout from provider"):
            await agent._request_with_retry("POST", "https://api.example.com/v1/chat/completions")

    assert agent.timeout_adjusted is False
    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_provider_native_tool_call_passthrough(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
            "tool_calling": "native",
        },
    )
    response = agent._process_chat_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": '{"path":"x.txt","content":"ok"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )
    tool_call = response["choices"][0]["message"]["tool_calls"][0]
    assert tool_call["function"]["name"] == "write_file"


@pytest.mark.asyncio
async def test_provider_unknown_native_tool_call_fails(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
            "tool_calling": "native",
        },
    )
    with pytest.raises(ValueError, match="Unknown tool_call"):
        agent._process_chat_response(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "dangerous_tool", "arguments": "{}"},
                                }
                            ],
                        }
                    }
                ]
            }
        )


@pytest.mark.asyncio
async def test_provider_invalid_native_tool_args_fail_schema(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
            "tool_calling": "native",
        },
    )
    with pytest.raises(ValueError, match="schema_validation_failed"):
        agent._process_chat_response(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "write_file",
                                        "arguments": '{"path":"x.txt"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        )


@pytest.mark.asyncio
async def test_provider_auto_tool_calling_uses_declared_support(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
            "tool_calling": "auto",
            "supports_tool_calling": True,
        },
    )
    response = agent._process_chat_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": '{"path":"x.txt","content":"ok"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )
    assert response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "write_file"


@pytest.mark.asyncio
async def test_provider_sse_parser_supports_multiline_events():
    agent = create_code_agent(
        "local-openai-compatible",
        {"agent_id": "test", "base_url": "http://localhost:1234/v1"},
    )

    class FakeResponse:
        async def aiter_lines(self):
            for line in [
                "event: message",
                'data: {"choices":[{"delta":{"content":"he"}}]}',
                'data: {"choices":[{"delta":{"content":"llo"}}]}',
                "",
                "data: [DONE]",
                "",
            ]:
                yield line

    events = []
    async for item in agent._iter_sse_data(FakeResponse()):
        events.append(item)
    assert events[0].startswith('{"choices"')
    assert events[1] == "[DONE]"


@pytest.mark.asyncio
async def test_provider_local_400_retries_with_simplified_history():
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
            "stream": False,
        },
    )

    payloads = []

    async def fake_request(method, url, **kwargs):
        payloads.append(kwargs.get("json", {}))
        if method == "GET":
            mock_models = MagicMock()
            mock_models.status_code = 200
            mock_models.json.return_value = {"data": [{"id": "model-1"}]}
            return mock_models
        if len(payloads) == 2:
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.request = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=mock_resp.request, response=mock_resp
            )
            return mock_resp
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type": "final", "payload": {"message": "done"}}',
                    }
                }
            ],
            "usage": {"total_tokens": 10},
        }
        return mock_resp

    messages = [
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1"}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "Tool ok"},
    ]

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        response = await agent.chat_completion(messages)

    assert response["choices"][0]["message"]["content"].startswith('{"action_type": "final"')
    assert len(payloads) == 3
    assert payloads[2]["stream"] is False
    assert "tools" not in payloads[2]
    assert all("tool_calls" not in message for message in payloads[2]["messages"])
    assert any(
        message["role"] == "user" and "Tool result:" in message["content"]
        for message in payloads[2]["messages"]
    )
    assert any(event["event"] == "llm.local_400_retry" for event in agent._provider_events)
    assert any(event["event"] == "llm.local_retry_mode" for event in agent._provider_events)


@pytest.mark.asyncio
async def test_provider_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    agent = create_code_agent(
        "anthropic",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "claude-3-5-sonnet",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [
            {
                "type": "text",
                "text": '{"type": "plan", "payload": {"reason": "planning"}}',
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20},
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        res = await agent.chat_completion(
            [
                {"role": "system", "content": "Sys prompt"},
                {"role": "user", "content": "User prompt"},
            ]
        )

    assert "choices" in res
    content = json.loads(res["choices"][0]["message"]["content"])
    assert content["action_type"] == "plan"
    assert res["usage"]["total_tokens"] == 30


@pytest.mark.asyncio
async def test_provider_google(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    agent = create_code_agent(
        "google",
        {
            "agent_id": "test",
            "model": "gemini-1.5-pro",
            "api_key_env": "GEMINI_API_KEY",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"type": "read_file", "reason": "reading", "payload":'
                                ' {"path": "a.txt"}}'
                            )
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {"totalTokenCount": 50},
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        res = await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert "choices" in res
    content = json.loads(res["choices"][0]["message"]["content"])
    assert content["action_type"] == "read_file"
    assert res["usage"]["total_tokens"] == 50


@pytest.mark.asyncio
async def test_provider_openai_missing_api_key_fails_validation():
    """Missing API key must fail with clear error, not default to stub."""
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
            "api_key_env": "OPENAI_API_KEY",
        },
    )
    with pytest.raises(ValueError, match="API key not found"):
        await agent.health_check()


@pytest.mark.asyncio
async def test_provider_openai_health_check_accepts_v1_base(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
            "api_key_env": "OPENAI_API_KEY",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "model-1"}]}

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        health = await agent.health_check()

    assert health["status"] == "healthy"
    request_url = mock_client.request.call_args.args[1]
    assert request_url == "http://fake/v1/models"


@patch("scripts.llm_harness.providers.httpx.AsyncClient")
@pytest.mark.asyncio
async def test_provider_control_plane_unavailable_clear_error(mock_client_cls):
    """ControlPlaneProvider must give clear error when runtime is unreachable."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    try:
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError(
            "Connection refused", request=MagicMock()
        )
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        agent = create_code_agent(
            "control-plane",
            {
                "agent_id": "test",
                "base_url": "http://localhost:9999",
            },
        )
        with pytest.raises(RuntimeError, match="Cannot connect to control plane"):
            await agent.chat_completion([{"role": "user", "content": "hi"}])
    finally:
        monkeypatch.undo()


@pytest.mark.asyncio
async def test_provider_openai_temperature_zero(monkeypatch):
    """OpenAI-compatible provider must send temperature=0 in the payload."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
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
                        "content": '{"type": "final", "payload": {"message": "done"}}',
                    }
                }
            ],
            "usage": {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
        }
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = capture_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert len(sent_payloads) >= 1
    assert sent_payloads[0].get("temperature") == 0
    assert sent_payloads[0].get("response_format") == {"type": "json_object"}


@pytest.mark.asyncio
async def test_provider_openai_response_format_fallback(monkeypatch):
    """When provider returns 400 for response_format, retry without it."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
            "max_retries": 1,
        },
    )

    sent_payloads = []
    call_count = 0

    async def request_with_fallback(method, url, **kwargs):
        nonlocal call_count
        sent_payloads.append(kwargs.get("json", {}))
        call_count += 1
        if call_count == 1:
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.request = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=mock_resp.request, response=mock_resp
            )
            return mock_resp
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type": "final", "payload": {"message": "done"}}',
                    }
                }
            ],
            "usage": {"total_tokens": 10},
        }
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = request_with_fallback
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert call_count == 2
    # First payload has response_format
    assert sent_payloads[0].get("response_format") == {"type": "json_object"}
    # Second payload (fallback) lacks response_format
    assert "response_format" not in sent_payloads[1]
    # Both have temperature=0
    assert sent_payloads[0].get("temperature") == 0
    assert sent_payloads[1].get("temperature") == 0


@pytest.mark.asyncio
async def test_provider_openai_disables_response_format_after_first_400(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
            "max_retries": 1,
        },
    )

    sent_payloads = []
    call_count = 0

    async def request_with_cached_fallback(method, url, **kwargs):
        nonlocal call_count
        sent_payloads.append(kwargs.get("json", {}))
        call_count += 1
        if call_count == 1:
            mock_resp = MagicMock()
            mock_resp.status_code = 400
            mock_resp.request = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad Request", request=mock_resp.request, response=mock_resp
            )
            return mock_resp
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type": "final", "payload": {"message": "done"}}',
                    }
                }
            ],
            "usage": {"total_tokens": 10},
        }
        return mock_resp

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = request_with_cached_fallback
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await agent.chat_completion([{"role": "user", "content": "hi"}])
        await agent.chat_completion([{"role": "user", "content": "hi again"}])

    assert call_count == 3
    assert sent_payloads[0].get("response_format") == {"type": "json_object"}
    assert "response_format" not in sent_payloads[1]
    assert "response_format" not in sent_payloads[2]


@pytest.mark.asyncio
async def test_provider_local_openai_skips_response_format(monkeypatch):
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
        },
    )

    sent_payloads = []
    call_count = 0

    async def capture_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        sent_payloads.append(kwargs.get("json", {}))
        if method == "GET":
            mock_models = MagicMock()
            mock_models.status_code = 200
            mock_models.json.return_value = {"data": [{"id": "model-1"}]}
            return mock_models
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"type": "final", "payload": {"message": "done"}}',
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

    assert call_count == 2
    assert "response_format" not in sent_payloads[-1]


@pytest.mark.asyncio
async def test_provider_openai_usage_in_response(monkeypatch):
    """OpenAI-compatible provider must include usage from API response."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"type": "final", "payload": {"message": "done"}}',
                }
            }
        ],
        "usage": {"total_tokens": 100, "prompt_tokens": 40, "completion_tokens": 60},
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        res = await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert res["usage"]["total_tokens"] == 100
    assert res["usage"]["prompt_tokens"] == 40
    assert res["usage"]["completion_tokens"] == 60


@pytest.mark.asyncio
async def test_provider_openai_usage_defaults_to_zero(monkeypatch):
    """When API response has no usage, provider must default to zero."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
        },
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"type": "final", "payload": {"message": "done"}}',
                }
            }
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        res = await agent.chat_completion([{"role": "user", "content": "hi"}])

    assert res["usage"]["total_tokens"] == 0
    assert res["usage"]["prompt_tokens"] == 0
    assert res["usage"]["completion_tokens"] == 0


def test_provider_secrets_redaction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-password")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
        },
    )
    # Safe repr must hide the secret
    assert "secret-password" not in repr(agent)

    raw = {"choices": [{"message": {"content": "api_key=secret-password"}}]}
    sanitized = agent._sanitize_response(raw)
    assert "secret-password" not in str(sanitized)
    assert "[REDACTED]" in str(sanitized)


@pytest.mark.asyncio
async def test_provider_local_openai_reasoning_content_fallback(monkeypatch):
    """Local provider must fall back to reasoning_content when content is empty."""
    agent = create_code_agent(
        "local-openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake/v1",
            "model": "model-1",
        },
    )

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {"data": [{"id": "model-1"}]}

    mock_chat_response = MagicMock()
    mock_chat_response.status_code = 200
    mock_chat_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": (
                        '{"type": "final", "payload": {"message": "from reasoning"}}'
                    ),
                }
            }
        ],
        "usage": {"total_tokens": 50, "completion_tokens_details": {"reasoning_tokens": 40}},
    }

    call_count = 0
    async def fake_request(method, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if method == "GET":
            return mock_models_response
        return mock_chat_response

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = fake_request
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await agent.chat_completion([{"role": "user", "content": "hi"}])

    content = json.loads(result["choices"][0]["message"]["content"])
    assert content["action_type"] == "final"
    assert content["message"] == "from reasoning"
    assert result["usage"]["completion_tokens_details"]["reasoning_tokens"] == 40


@pytest.mark.asyncio
async def test_provider_openai_max_tokens_in_payload(monkeypatch):
    """OpenAI-compatible provider must include max_tokens in payload when configured."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
            "max_tokens": 4096,
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
                        "content": '{"type": "final", "payload": {"message": "done"}}',
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

    assert sent_payloads[0].get("max_tokens") == 4096


@pytest.mark.asyncio
async def test_provider_openai_no_max_tokens_when_unset(monkeypatch):
    """When max_tokens is not configured, it must not appear in the payload."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
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
                        "content": '{"type": "final", "payload": {"message": "done"}}',
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

    assert "max_tokens" not in sent_payloads[0]


@pytest.mark.asyncio
async def test_provider_reasoning_content_empty_raises_error(monkeypatch):
    """Provider must still raise ValueError when both content and reasoning_content are empty."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    agent = create_code_agent(
        "openai-compatible",
        {
            "agent_id": "test",
            "base_url": "http://fake",
            "model": "model-1",
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
                    "reasoning_content": "",
                }
            }
        ]
    }

    with patch("scripts.llm_harness.providers.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValueError, match="empty content"):
            await agent.chat_completion([{"role": "user", "content": "hi"}])
