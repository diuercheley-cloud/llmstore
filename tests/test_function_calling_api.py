import json
from decimal import Decimal

import pytest
from httpx import AsyncClient
from starlette.responses import JSONResponse

from app.api.deps import get_inference_proxy
from app.main import app
from app.services.billing.core import EffectivePlan
from app.services.inference_proxy import ForwardResult
from app.utils.tool_calling import validate_tool_schema


class FakeToolProxy:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    async def chat(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return ForwardResult(
            response=JSONResponse(content=self.payload),
            backend_name="fake-tools-backend",
            attempts=1,
            fallback_used=False,
            backend_errors=[],
        )


@pytest.fixture
def tools_enabled_plan(monkeypatch):
    plan = EffectivePlan(
        code="test",
        name="Test",
        rate_limit_per_minute=1000,
        daily_token_quota=1_000_000,
        weekly_token_quota=2_000_000,
        monthly_token_quota=4_000_000,
        max_output_tokens=4096,
        allow_streaming=True,
        max_context_tokens=32768,
        overage_price_per_1k_tokens=Decimal("0"),
        responses_enabled=True,
        tools_enabled=True,
        embeddings_enabled=True,
        embeddings_requests_per_month=1000,
        embeddings_tokens_per_month=1_000_000,
    )
    monkeypatch.setattr("app.api.client.resolve_effective_plan", lambda client: plan)
    monkeypatch.setattr("app.utils.validation.resolve_effective_plan", lambda client: plan)
    return plan


@pytest.fixture
def tools_disabled_plan(monkeypatch):
    plan = EffectivePlan(
        code="test-no-tools",
        name="Test No Tools",
        rate_limit_per_minute=1000,
        daily_token_quota=1_000_000,
        weekly_token_quota=2_000_000,
        monthly_token_quota=4_000_000,
        max_output_tokens=4096,
        allow_streaming=True,
        max_context_tokens=32768,
        overage_price_per_1k_tokens=Decimal("0"),
        responses_enabled=True,
        tools_enabled=False,
        embeddings_enabled=True,
        embeddings_requests_per_month=1000,
        embeddings_tokens_per_month=1_000_000,
    )
    monkeypatch.setattr("app.api.client.resolve_effective_plan", lambda client: plan)
    monkeypatch.setattr("app.utils.validation.resolve_effective_plan", lambda client: plan)
    return plan


@pytest.fixture
def proxy_factory():
    created: list[FakeToolProxy] = []

    def factory(payload: dict) -> FakeToolProxy:
        proxy = FakeToolProxy(payload)
        created.append(proxy)
        app.dependency_overrides[get_inference_proxy] = lambda: proxy
        return proxy

    yield factory
    app.dependency_overrides.pop(get_inference_proxy, None)


async def _create_backend_model_and_key(
    admin_client: AsyncClient,
    admin_token_headers: dict[str, str],
    *,
    provider: str,
    backend_name: str,
    model_id: str,
    models_dir=None,
) -> str:
    resp = await admin_client.post(
        "/admin/backends",
        json={
            "name": backend_name,
            "provider": provider,
            "backend_url": "http://localhost:8081",
            "healthcheck_path": "/v1/models",
            "is_active": True,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    backend_id = resp.json()["id"]

    model_file = f"{model_id}.gguf"
    if provider == "llama.cpp" and models_dir is not None:
        (models_dir / model_file).touch()

    resp = await admin_client.post(
        "/admin/models",
        json={
            "display_name": model_id,
            "model_id": model_id,
            "model_alias": model_id,
            "provider": provider,
            "model_file": model_file,
            "inference_backend_id": backend_id,
            "is_active": True,
            "is_default": True,
            "context_length": 4096,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201

    resp = await admin_client.post(
        "/admin/clients",
        json={"name": f"{model_id}-client", "rate_limit_per_minute": 100},
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    resp = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": f"{model_id}-key"},
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    return resp.json()["api_key"]


@pytest.mark.asyncio
async def test_chat_completions_tools_auto_logs_sanitized(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy = proxy_factory(
        {
            "id": "chatcmpl-tools-1",
            "object": "chat.completion",
            "created": 1710000000,
            "model": "tools-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_weather_1",
                                "type": "function",
                                "function": {
                                    "name": "weather_mock",
                                    "arguments": json.dumps({"city": "Sao Paulo", "api_key": "secret-123"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="openai-tools-backend",
        model_id="tools-model",
    )

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "tools-model",
            "messages": [{"role": "user", "content": "Qual o clima em Sao Paulo?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "weather_mock",
                        "description": "Retorna clima mockado",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    },
                }
            ],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["finish_reason"] == "tool_calls"
    assert body["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "weather_mock"

    forwarded = proxy.calls[-1]["args"][0]
    assert forwarded["tool_choice"] == "auto"
    assert forwarded["parallel_tool_calls"] is True
    assert forwarded["tools"][0]["function"]["name"] == "weather_mock"

    logs = await admin_client.get("/admin/requests", headers=admin_token_headers)
    assert logs.status_code == 200
    latest = logs.json()[0]
    assert latest["tool_call_count"] == 1
    assert latest["had_tool_call"] is True
    assert latest["tool_calls"][0]["function"]["name"] == "weather_mock"
    assert "secret-123" not in latest["tool_calls"][0]["function"]["arguments_preview"]
    assert '"api_key"' in latest["tool_calls"][0]["function"]["arguments_preview"]


@pytest.mark.asyncio
async def test_chat_completions_ignores_inert_tool_fields_without_tools(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_disabled_plan,
):
    proxy = proxy_factory(
        {
            "id": "chatcmpl-no-tools-1",
            "object": "chat.completion",
            "created": 1710000006,
            "model": "no-tools-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="no-tools-backend",
        model_id="no-tools-model",
    )

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "no-tools-model",
            "messages": [{"role": "user", "content": "oi"}],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200

    forwarded = proxy.calls[-1]["args"][0]
    assert "tools" not in forwarded
    assert "tool_choice" not in forwarded
    assert "parallel_tool_calls" not in forwarded


@pytest.mark.asyncio
async def test_chat_completions_tools_specific_choice_forwarded(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy = proxy_factory(
        {
            "id": "chatcmpl-tools-2",
            "object": "chat.completion",
            "created": 1710000001,
            "model": "tools-model-specific",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="openai-tools-backend-specific",
        model_id="tools-model-specific",
    )

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "tools-model-specific",
            "messages": [{"role": "user", "content": "Use weather_mock"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "weather_mock",
                        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "weather_mock"}},
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200
    forwarded = proxy.calls[-1]["args"][0]
    assert forwarded["tool_choice"]["function"]["name"] == "weather_mock"


@pytest.mark.asyncio
async def test_chat_completions_invalid_tool_schema_rejected(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy_factory(
        {
            "id": "unused",
            "object": "chat.completion",
            "created": 1710000002,
            "model": "invalid-schema-model",
            "choices": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="invalid-schema-backend",
        model_id="invalid-schema-model",
    )

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "invalid-schema-model",
            "messages": [{"role": "user", "content": "teste"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "weather_mock",
                        "parameters": {
                            "type": "object",
                            "$ref": "#/definitions/secret",
                        },
                    },
                }
            ],
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "tool_schema_not_allowed"


@pytest.mark.asyncio
async def test_chat_completions_allows_anyof_tool_schema(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy = proxy_factory(
        {
            "id": "chatcmpl-tools-anyof",
            "object": "chat.completion",
            "created": 1710000006,
            "model": "anyof-tools-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "ok",
                        "tool_calls": [],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="anyof-tools-backend",
        model_id="anyof-tools-model",
    )

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "anyof-tools-model",
            "messages": [{"role": "user", "content": "teste"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "weather_mock",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "anyOf": [
                                        {"type": "string"},
                                        {"type": "null"},
                                    ]
                                }
                            },
                        },
                    },
                }
            ],
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200
    forwarded = proxy.calls[-1]["args"][0]
    assert forwarded["tools"][0]["function"]["parameters"]["properties"]["query"]["anyOf"][0]["type"] == "string"


def test_validate_tool_schema_depth_uses_structural_nesting(monkeypatch):
    monkeypatch.setattr("app.utils.tool_calling.settings.max_tool_schema_depth", 8)
    schema = {
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["field", "value"],
                        },
                    }
                },
                "required": ["filters"],
            }
        },
        "required": ["request"],
    }

    validate_tool_schema(schema, tool_name="question")


def test_validate_tool_schema_rejects_true_structural_depth_over_limit(monkeypatch):
    monkeypatch.setattr("app.utils.tool_calling.settings.max_tool_schema_depth", 8)
    schema = {
        "type": "object",
        "properties": {
            "level1": {
                "type": "object",
                "properties": {
                    "level2": {
                        "type": "object",
                        "properties": {
                            "level3": {
                                "type": "object",
                                "properties": {
                                    "level4": {
                                        "type": "object",
                                        "properties": {
                                            "level5": {
                                                "type": "object",
                                                "properties": {
                                                    "level6": {
                                                        "type": "object",
                                                        "properties": {
                                                            "level7": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "level8": {"type": "string"}
                                                                },
                                                            }
                                                        },
                                                    }
                                                },
                                            }
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
            }
        },
    }

    with pytest.raises(Exception) as exc_info:
        validate_tool_schema(schema, tool_name="question")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "tool_schema_too_deep"


@pytest.mark.asyncio
async def test_chat_completions_large_tool_payload_rejected(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy_factory(
        {
            "id": "unused-large",
            "object": "chat.completion",
            "created": 1710000003,
            "model": "large-tool-model",
            "choices": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="large-tool-backend",
        model_id="large-tool-model",
    )
    properties = {f"field_{idx}": {"type": "string"} for idx in range(300)}

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "large-tool-model",
            "messages": [{"role": "user", "content": "teste"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "weather_mock",
                        "parameters": {"type": "object", "properties": properties},
                    },
                }
            ],
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "tool_schema_too_large"


@pytest.mark.asyncio
async def test_chat_completions_provider_without_tools_returns_capability_error(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy = proxy_factory(
        {
            "id": "should-not-run",
            "object": "chat.completion",
            "created": 1710000004,
            "model": "local-no-tools-model",
            "choices": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="ollama",
        backend_name="ollama-no-tools-backend",
        model_id="local-no-tools-model",
    )

    resp = await admin_client.post(
        "/v1/chat/completions",
        json={
            "model": "local-no-tools-model",
            "messages": [{"role": "user", "content": "teste"}],
            "tools": [{"type": "function", "function": {"name": "weather_mock"}}],
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "capability_not_supported"
    assert proxy.calls == []


@pytest.mark.asyncio
async def test_responses_accepts_tools_for_supported_provider(
    admin_client: AsyncClient,
    admin_token_headers,
    proxy_factory,
    tools_enabled_plan,
):
    proxy_factory(
        {
            "id": "chatcmpl-tools-response",
            "object": "chat.completion",
            "created": 1710000005,
            "model": "responses-tools-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_weather_2",
                                "type": "function",
                                "function": {
                                    "name": "weather_mock",
                                    "arguments": "{\"city\":\"Campinas\"}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 3, "total_tokens": 12},
        }
    )
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="responses-tools-backend",
        model_id="responses-tools-model",
    )

    resp = await admin_client.post(
        "/v1/responses",
        json={
            "model": "responses-tools-model",
            "input": "Consulte o clima",
            "tools": [{"type": "function", "function": {"name": "weather_mock"}}],
            "tool_choice": "auto",
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "response"
    assert body["output_text"] == ""
    assert body["output"][0]["type"] == "function_call"
    assert body["output"][0]["name"] == "weather_mock"
    assert body["output"][0]["arguments"] == "{\"city\":\"Campinas\"}"


@pytest.mark.asyncio
async def test_v1_models_reports_tool_capability_for_openai_compatible(
    admin_client: AsyncClient,
    admin_token_headers,
):
    api_key = await _create_backend_model_and_key(
        admin_client,
        admin_token_headers,
        provider="openai_compatible",
        backend_name="models-tools-backend",
        model_id="models-tools-model",
    )

    resp = await admin_client.get("/v1/models", headers={"Authorization": f"Bearer {api_key}"})
    assert resp.status_code == 200
    model = next(item for item in resp.json()["data"] if item["id"] == "models-tools-model")
    assert model["capabilities"]["tools"] is True
