import pytest
from httpx import AsyncClient
from pathlib import Path

@pytest.mark.asyncio
async def test_admin_deep_health(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/health/deep", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data

@pytest.mark.asyncio
async def test_admin_cache_stats(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/cache/stats", headers=admin_token_headers)
    assert response.status_code == 200
    assert "entries_total" in response.json()

@pytest.mark.asyncio
async def test_admin_list_model_files(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/models/files", headers=admin_token_headers)
    assert response.status_code == 200
    assert "files" in response.json()

@pytest.mark.asyncio
async def test_admin_test_prompt(admin_client: AsyncClient, admin_token_headers, models_dir: Path):
    # Ensure file exists
    (models_dir / "test.gguf").touch()
    
    # Create model first
    create_payload = {
        "model_id": "test/prompt",
        "provider": "llama.cpp",
        "model_file": "test.gguf",
        "is_active": True
    }
    create_resp = await admin_client.post("/admin/models", json=create_payload, headers=admin_token_headers)
    assert create_resp.status_code == 201
    model_uuid = create_resp.json()["id"]

    # Test prompt (will fail to connect to backend, but endpoint should be reachable)
    test_payload = {
        "prompt": "Hello",
        "max_tokens": 10
    }
    resp = await admin_client.post(f"/admin/models/{model_uuid}/test-prompt", json=test_payload, headers=admin_token_headers)
    # It might fail with 503 or 409 depending on backend connectivity in test env
    assert resp.status_code in [200, 409, 503]
