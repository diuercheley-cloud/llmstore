import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_hybrid_summary_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/summary")
    assert resp.status_code in (401, 403), "Should require admin auth"


@pytest.mark.asyncio
async def test_hybrid_summary_returns_valid_json(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/summary", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()

    expected_fields = [
        "total_requests",
        "local_requests",
        "cloud_requests",
        "cache_hit_rate",
        "provider_cost_brl",
        "customer_revenue_brl",
        "gross_profit_brl",
        "margin_percent",
        "active_wallets",
        "low_balance_clients",
        "providers_enabled",
        "providers_configured",
        "warnings",
        "critical_failures",
        "cloud_enabled",
        "local_first",
        "timestamp",
    ]
    for field in expected_fields:
        assert field in data, f"Field '{field}' missing in hybrid summary"

    assert isinstance(data["warnings"], list)
    assert isinstance(data["critical_failures"], list)
    assert isinstance(data["total_requests"], int)
    assert isinstance(data["margin_percent"], float)


@pytest.mark.asyncio
async def test_hybrid_providers_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/providers")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_hybrid_providers_returns_list(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/providers", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        p = data[0]
        assert "provider_id" in p
        assert "provider_type" in p
        assert "enabled" in p
        assert "configured" in p
        assert "masked_api_key" in p
        assert "capabilities" in p


@pytest.mark.asyncio
async def test_hybrid_routing_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/routing")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_hybrid_routing_returns_data(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/routing", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "default_strategy" in data
    assert "cloud_providers_enabled" in data
    assert "last_decisions" in data
    assert isinstance(data["last_decisions"], list)


@pytest.mark.asyncio
async def test_hybrid_financials_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/financials")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_hybrid_financials_returns_data(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/financials", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "provider_costs" in data
    assert "costs_config" in data


@pytest.mark.asyncio
async def test_hybrid_cache_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/cache")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_hybrid_cache_returns_data(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/cache", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "exact_cache_enabled" in data
    assert "semantic_cache_enabled" in data
    assert "ttl_seconds" in data
    assert "exact_hits" in data


@pytest.mark.asyncio
async def test_hybrid_wallets_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/wallets")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_hybrid_wallets_returns_data(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/wallets", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_hybrid_rag_requires_auth(admin_client: AsyncClient):
    resp = await admin_client.get("/admin/hybrid/rag")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_hybrid_rag_returns_data(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    resp = await admin_client.get("/admin/hybrid/rag", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "rag_enabled" in data
    assert "embedding_provider" in data
    assert "total_documents" in data
    assert "total_chunks" in data
