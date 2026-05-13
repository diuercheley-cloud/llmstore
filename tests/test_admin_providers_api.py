import os
import pytest
from httpx import AsyncClient

from app.services.providers.registry import reload_registry


@pytest.fixture(autouse=True)
def reset_registry():
    reload_registry()
    yield
    reload_registry()


@pytest.mark.asyncio
async def test_admin_providers_list_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/providers", headers={})
    assert resp.status_code in (401, 403), "Should require auth"


@pytest.mark.asyncio
async def test_admin_providers_list_with_auth(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/providers", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = [p["provider_id"] for p in data]
    assert "local" in ids
    assert "openai" in ids
    assert "anthropic" in ids
    assert "deepseek" in ids


@pytest.mark.asyncio
async def test_admin_providers_detail(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/providers/local", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider_id"] == "local"
    assert data["enabled"] is True
    assert data["configured"] is True


@pytest.mark.asyncio
async def test_admin_providers_not_found(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/providers/nonexistent", headers={"X-Admin-Token": token})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_providers_health(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/providers/local/health", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider_id"] == "local"


@pytest.mark.asyncio
async def test_admin_providers_capabilities(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/providers/capabilities/all", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "local" in data
    assert "openai" in data

    local_caps = data["local"]
    assert local_caps["chat"] is True
    assert local_caps["embeddings"] is True
