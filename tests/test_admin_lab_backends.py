import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_backends(admin_client: AsyncClient, admin_token_headers):
    response = await admin_client.get("/admin/backends", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_and_patch_backend(admin_client: AsyncClient, admin_token_headers):
    # Create
    payload = {
        "name": "test-backend",
        "provider": "llama.cpp",
        "backend_url": "http://localhost:8080",
        "healthcheck_path": "/health",
        "is_active": True,
        "is_default": False,
        "status": "configured",
        "max_parallel_requests": 1
    }
    resp = await admin_client.post("/admin/backends", json=payload, headers=admin_token_headers)
    assert resp.status_code == 201
    backend_id = resp.json()["id"]

    # Patch
    patch_payload = {"name": "test-backend-updated"}
    resp = await admin_client.patch(f"/admin/backends/{backend_id}", json=patch_payload, headers=admin_token_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-backend-updated"

@pytest.mark.asyncio
async def test_backend_health_and_logs_endpoints(admin_client: AsyncClient, admin_token_headers):
    # Create
    payload = {
        "name": "health-test",
        "provider": "llama.cpp",
        "backend_url": "http://localhost:8080",
        "is_active": True
    }
    resp = await admin_client.post("/admin/backends", json=payload, headers=admin_token_headers)
    backend_id = resp.json()["id"]

    # Health
    resp = await admin_client.get(f"/admin/backends/{backend_id}/health", headers=admin_token_headers)
    assert resp.status_code == 200
    assert "backend" in resp.json()
    assert "docker" in resp.json()

    # Logs (should fail with 409 if no service_name in metadata)
    resp = await admin_client.get(f"/admin/backends/{backend_id}/logs", headers=admin_token_headers)
    assert resp.status_code == 409
    assert "service_name" not in resp.json() or resp.json()["detail"] == "backend is not mapped to a compose service"
