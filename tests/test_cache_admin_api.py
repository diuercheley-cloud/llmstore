import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_cache_stats(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/cache/stats", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "exact_entries" in data
    assert "semantic_entries" in data
    assert "entries_total" in data
    assert "cache_hit_rate" in data


@pytest.mark.asyncio
async def test_admin_cache_entries(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/cache/entries", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "total" in data
    assert isinstance(data["entries"], list)


@pytest.mark.asyncio
async def test_admin_cache_invalidate(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.post("/admin/cache/invalidate", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalidated"
    assert "exact_deleted" in data
    assert "semantic_deleted" in data


@pytest.mark.asyncio
async def test_admin_cache_policies(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/cache/policies", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
