import pytest
from app.api.deps import get_inference_proxy
from app.main import app
from app.services.inference_proxy import ForwardResult
from httpx import AsyncClient
from starlette.responses import JSONResponse


class FakeProxy:
    def __init__(self):
        self.calls = []

    async def chat(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        content = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! I am a fake response.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 12, "total_tokens": 21},
        }
        return ForwardResult(
            response=JSONResponse(content=content, headers={"X-Upstream-Fallback": "false"}),
            backend_name="fake-backend",
            attempts=1,
            fallback_used=False,
            backend_errors=[],
        )


@pytest.fixture
def mock_proxy():
    proxy = FakeProxy()
    app.dependency_overrides[get_inference_proxy] = lambda: proxy
    yield proxy
    app.dependency_overrides.pop(get_inference_proxy, None)


@pytest.mark.asyncio
async def test_responses_api_basic_string(admin_client: AsyncClient, mock_proxy):
    assert mock_proxy.calls == []


@pytest.mark.asyncio
async def test_responses_api_full_flow(admin_client: AsyncClient, mock_proxy, admin_token_headers):
    # 0. Setup backend and model
    resp = await admin_client.post(
        "/admin/backends",
        json={
            "name": "test-backend",
            "provider": "openai_compatible",
            "backend_url": "http://localhost:8081",
            "is_active": True,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    backend_id = resp.json()["id"]

    resp = await admin_client.post(
        "/admin/models",
        json={
            "display_name": "Default Model",
            "model_id": "default",
            "model_alias": "default",
            "provider": "openai_compatible",
            "model_file": "default.gguf",
            "inference_backend_id": backend_id,
            "is_active": True,
            "is_default": True,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201

    # 1. Create a client
    resp = await admin_client.post(
        "/admin/clients",
        json={
            "name": "test-client",
            "description": "test",
            "rate_limit_per_minute": 10,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    # 2. Create an API key
    resp = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": "test-key"},
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    api_key = resp.json()["api_key"]

    # 3. Call /v1/responses
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "default",
        "input": "Hello",
        "instructions": "Be fake.",
        "metadata": {"test": "true"},
    }
    resp = await admin_client.post("/v1/responses", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "response"
    assert data["created_at"] == 1677652288
    assert data["output_text"] == "Hello! I am a fake response."
    assert data["output"] == [
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Hello! I am a fake response."}],
            },
        }
    ]
    assert data["metadata"] == {"test": "true"}
    assert "usage" in data
    assert resp.headers["X-Requested-Model"] == "default"
    assert resp.headers["X-Resolved-Model"] == "default"
    assert resp.headers["X-Backend-Name"] == "fake-backend"
    assert resp.headers["X-Fallback-Used"] == "false"
    assert resp.headers["X-Upstream-Fallback"] == "false"

    forwarded = mock_proxy.calls[-1]["args"][0]
    assert forwarded["messages"] == [
        {"role": "system", "content": "Be fake."},
        {"role": "user", "content": "Hello"},
    ]


@pytest.mark.asyncio
async def test_responses_api_array_input(
    admin_client: AsyncClient, mock_proxy, admin_token_headers
):
    resp = await admin_client.post(
        "/admin/backends",
        json={
            "name": "array-backend",
            "provider": "openai_compatible",
            "backend_url": "http://localhost:8081",
            "is_active": True,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    backend_id = resp.json()["id"]

    resp = await admin_client.post(
        "/admin/models",
        json={
            "display_name": "Array Model",
            "model_id": "default",
            "model_alias": "default",
            "provider": "openai_compatible",
            "model_file": "default.gguf",
            "inference_backend_id": backend_id,
            "is_active": True,
            "is_default": True,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201

    resp = await admin_client.post(
        "/admin/clients",
        json={
            "name": "array-client",
            "description": "test",
            "rate_limit_per_minute": 10,
        },
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    resp = await admin_client.post(
        "/admin/api-keys",
        json={"client_id": client_id, "name": "array-key"},
        headers=admin_token_headers,
    )
    assert resp.status_code == 201
    api_key = resp.json()["api_key"]

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "default",
        "input": [
            "Primeira linha",
            {"role": "assistant", "content": "Contexto anterior"},
            {"role": "user", "content": [{"type": "input_text", "text": "Pergunta atual"}]},
        ],
    }
    resp = await admin_client.post("/v1/responses", json=payload, headers=headers)
    assert resp.status_code == 200

    forwarded = mock_proxy.calls[-1]["args"][0]
    assert forwarded["messages"] == [
        {"role": "user", "content": "Primeira linha"},
        {"role": "assistant", "content": "Contexto anterior"},
        {"role": "user", "content": "Pergunta atual"},
    ]
