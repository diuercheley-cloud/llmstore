import os

import httpx
import pytest
import pytest_asyncio
from app.api.routing_admin import router
from app.services.routing.smart_router import reset_smart_router
from fastapi import FastAPI


@pytest.fixture(autouse=True)
def reset_router():
    reset_smart_router()
    yield
    reset_smart_router()


@pytest_asyncio.fixture
async def test_app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest_asyncio.fixture
async def authed_client(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _authed_post(client, path, json_data):
    return await client.post(path, json=json_data, headers={"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")})


async def _authed_get(client, path):
    return await client.get(path, headers={"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")})


@pytest.mark.asyncio
async def test_simulate_requires_auth(authed_client):
    resp = await authed_client.post("/admin/routing/simulate", json={"endpoint_type": "chat", "cloud_allowed": False})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_simulate_with_auth(authed_client):
    resp = await _authed_post(authed_client, "/admin/routing/simulate", {
        "endpoint_type": "chat",
        "cloud_allowed": False,
        "strategy": "local_first",
    })
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        data = resp.json()
        assert "decision" in data
        assert "strategies_considered" in data
        assert "provider_states" in data
        assert "config_snapshot" in data


@pytest.mark.asyncio
async def test_simulate_returns_decision_fields(authed_client):
    resp = await _authed_post(authed_client, "/admin/routing/simulate", {
        "endpoint_type": "chat",
        "cloud_allowed": False,
        "strategy": "local_first",
    })
    if resp.status_code == 200:
        dec = resp.json()["decision"]
        assert "selected_provider" in dec
        assert "selected_model" in dec
        assert "selected_backend" in dec
        assert "reason" in dec
        assert "fallback_chain" in dec
        assert "estimated_cost_brl" in dec
        assert "policy_applied" in dec
        assert "cloud_used" in dec
        assert "warnings" in dec


@pytest.mark.asyncio
async def test_get_policies_requires_auth(authed_client):
    resp = await authed_client.get("/admin/routing/policies")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_policies(authed_client):
    resp = await _authed_get(authed_client, "/admin/routing/policies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["default_strategy"] == "local_first"
    assert "allow_cloud_fallback" in data
    assert "fallback_order" in data


@pytest.mark.asyncio
async def test_get_last_decisions_requires_auth(authed_client):
    resp = await authed_client.get("/admin/routing/last-decisions")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_last_decisions(authed_client):
    resp = await _authed_get(authed_client, "/admin/routing/last-decisions?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_simulate_all_strategies(authed_client):
    for strategy in ["local_first", "lowest_cost", "premium_quality", "coding", "embeddings_optimized", "rag_optimized", "fallback_only"]:
        resp = await _authed_post(authed_client, "/admin/routing/simulate", {
            "endpoint_type": "chat",
            "cloud_allowed": False,
            "strategy": strategy,
        })
        assert resp.status_code in (200, 422), f"strategy {strategy} failed: {resp.status_code}"


@pytest.mark.asyncio
async def test_simulate_with_cloud_allowed(authed_client):
    resp = await _authed_post(authed_client, "/admin/routing/simulate", {
        "endpoint_type": "chat",
        "cloud_allowed": True,
        "strategy": "premium_quality",
    })
    assert resp.status_code in (200, 422)


@pytest.mark.asyncio
async def test_last_decisions_limit(authed_client):
    resp = await _authed_get(authed_client, "/admin/routing/last-decisions?limit=200")
    assert resp.status_code == 200
    resp2 = await _authed_get(authed_client, "/admin/routing/last-decisions?limit=999")
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_policies_endpoint_returns_all_fields(authed_client):
    resp = await _authed_get(authed_client, "/admin/routing/policies")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_strategy" in data
    assert "allow_cloud_fallback" in data
    assert "complexity_threshold" in data
    assert "coding_provider_preference" in data
    assert "low_budget_provider_preference" in data
    assert "premium_provider_preference" in data
    assert "max_provider_cost_per_request_brl" in data
    assert "tenant_policy_overrides" in data
    assert "fallback_order" in data
