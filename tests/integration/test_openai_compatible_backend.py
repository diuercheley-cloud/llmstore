import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_openai_compatible_backend(admin_client: AsyncClient, admin_token_headers):
    payload = {
        "name": "lmstudio-test",
        "provider": "openai_compatible",
        "backend_url": "http://192.168.101.1:1234/v1",
        "healthcheck_path": "/v1/models",
        "is_active": True,
        "metadata_json": json.dumps({"api_key": "test-key"}),
    }
    resp = await admin_client.post("/admin/backends", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "openai_compatible"
    assert "api_key" in data["metadata_json"]


@pytest.mark.asyncio
async def test_test_connection_endpoint(admin_client: AsyncClient, admin_token_headers):
    # This might fail if the proxy can't reach the URL, but we're testing the endpoint existence and schema
    payload = {
        "name": "test-conn",
        "provider": "openai_compatible",
        "backend_url": "http://localhost:1234/v1",
        "healthcheck_path": "/v1/models",
    }
    resp = await admin_client.post(
        "/admin/backends/test-connection", json=payload, headers=admin_token_headers
    )
    # Even if connection fails, it should return 200 with ok: false (unless it's a validation error)
    assert resp.status_code == 200
    assert "ok" in resp.json()


@pytest.mark.asyncio
async def test_list_models_endpoint(admin_client: AsyncClient, admin_token_headers):
    payload = {
        "name": "test-list",
        "provider": "openai_compatible",
        "backend_url": "http://localhost:1234/v1",
        "healthcheck_path": "/v1/models",
    }
    resp = await admin_client.post(
        "/admin/backends/list-models", json=payload, headers=admin_token_headers
    )
    # This might return 503 if localhost:1234 is not up, which is fine for schema test
    assert resp.status_code in [200, 503]
