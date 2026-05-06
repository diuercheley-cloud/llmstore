import pytest
import json
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_lmstudio_config_normalization(admin_client: AsyncClient, admin_token_headers):
    # Test with /v1
    payload = {
        "name": "lmstudio-v1",
        "provider": "openai_compatible",
        "backend_url": "http://192.168.101.1:1234/v1",
        "healthcheck_path": "/v1/models"
    }
    resp = await admin_client.post("/admin/backends", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    assert resp.json()["backend_url"] == "http://192.168.101.1:1234/v1"

    # Test without /v1
    payload = {
        "name": "lmstudio-root",
        "provider": "openai_compatible",
        "backend_url": "http://192.168.101.1:1234",
        "healthcheck_path": "/models"
    }
    resp = await admin_client.post("/admin/backends", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    assert resp.json()["backend_url"] == "http://192.168.101.1:1234"

@pytest.mark.asyncio
async def test_lmstudio_api_key_storage(admin_client: AsyncClient, admin_token_headers):
    payload = {
        "name": "lmstudio-with-key",
        "provider": "openai_compatible",
        "backend_url": "http://192.168.101.1:1234/v1",
        "metadata_json": json.dumps({"api_key": "sk-test-123"})
    }
    resp = await admin_client.post("/admin/backends", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    backend = resp.json()
    metadata = json.loads(backend["metadata_json"])
    assert metadata["api_key"] == "sk-test-123"
