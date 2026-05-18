import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import HTTPException

from app.api.client import _should_fallback_to_default_model

@pytest_asyncio.fixture
async def portal_client_data(admin_client: AsyncClient, admin_token_headers):
    resp = await admin_client.post(
        "/admin/clients",
        headers=admin_token_headers,
        json={"name": "Portal Test Client", "rate_limit_per_minute": 10}
    )
    client_data = resp.json()
    client_id = client_data["id"]
    resp = await admin_client.post(
        "/admin/api-keys",
        headers=admin_token_headers,
        json={"client_id": client_id, "name": "Portal Test Key"}
    )
    key_data = resp.json()
    return {"id": client_id, "api_key": key_data["api_key"]}

@pytest.mark.asyncio
async def test_portal_me(admin_client: AsyncClient, portal_client_data):
    response = await admin_client.get(
        "/portal/me",
        headers={"Authorization": f"Bearer {portal_client_data['api_key']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == portal_client_data["id"]
    assert "plan" in data

@pytest.mark.asyncio
async def test_portal_models(admin_client: AsyncClient, portal_client_data):
    response = await admin_client.get(
        "/portal/models",
        headers={"Authorization": f"Bearer {portal_client_data['api_key']}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_portal_models_hides_provider_unavailable_models(
    admin_client: AsyncClient,
    portal_client_data,
    admin_token_headers,
    monkeypatch,
):
    backend_resp = await admin_client.post(
        "/admin/backends",
        headers=admin_token_headers,
        json={
            "name": "openrouter-test",
            "provider": "openrouter",
            "backend_url": "https://openrouter.ai/api/v1",
            "healthcheck_path": "/models",
            "is_active": True,
        },
    )
    assert backend_resp.status_code == 201
    backend_id = backend_resp.json()["id"]

    model_resp = await admin_client.post(
        "/admin/models",
        headers=admin_token_headers,
        json={
            "model_id": "meta-llama/llama-3-8b-instruct:free",
            "display_name": "Unavailable OpenRouter Model",
            "provider": "openrouter",
            "model_file": "unused",
            "inference_backend_id": backend_id,
            "is_active": True,
        },
    )
    assert model_resp.status_code == 201

    class FakeProvider:
        async def list_models(self):
            return ["openai/gpt-4o-mini"]

    monkeypatch.setattr("app.api.portal.get_provider", lambda provider_id: FakeProvider() if provider_id == "openrouter" else None)

    response = await admin_client.get(
        "/portal/models",
        headers={"Authorization": f"Bearer {portal_client_data['api_key']}"},
    )
    assert response.status_code == 200
    model_ids = {item["id"] for item in response.json()}
    assert "meta-llama/llama-3-8b-instruct:free" not in model_ids


def test_unavailable_provider_model_404_triggers_default_fallback():
    exc = HTTPException(
        status_code=404,
        detail={
            "message": "data plane rejected request",
            "backend_status_code": 404,
            "backend_response": {
                "error": {
                    "message": "No endpoints found for meta-llama/llama-3-8b-instruct:free.",
                    "code": 404,
                }
            },
        },
    )
    assert _should_fallback_to_default_model(exc) is True


def test_non_endpoint_404_does_not_trigger_default_fallback():
    exc = HTTPException(
        status_code=404,
        detail={
            "message": "data plane rejected request",
            "backend_status_code": 404,
            "backend_response": {
                "error": {
                    "message": "Model temporarily unavailable.",
                    "code": 404,
                }
            },
        },
    )
    assert _should_fallback_to_default_model(exc) is False
