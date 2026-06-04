import os

import httpx
import pytest
import pytest_asyncio
from app.api.billing_admin import router
from fastapi import FastAPI


@pytest_asyncio.fixture
async def test_app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest_asyncio.fixture
async def client(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _get(url, client, headers=None):
    h = headers or {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    return await client.get(url, headers=h)


async def _post(url, json_data, client, headers=None):
    h = headers or {"X-Admin-Token": os.environ.get("ADMIN_TOKEN", "test-admin-token")}
    return await client.post(url, json=json_data, headers=h)


@pytest.mark.asyncio
async def test_provider_costs_requires_auth(client):
    resp = await client.get("/admin/billing/provider-costs")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_provider_costs(client):
    resp = await _get("/admin/billing/provider-costs", client)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for item in data:
        assert "provider" in item
        assert "cost_usd_per_1k_prompt" in item
        assert "pricing_configured" in item


@pytest.mark.asyncio
async def test_margins_summary_requires_auth(client):
    resp = await client.get("/admin/billing/margins/summary")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_margins_summary_requires_auth(client):
    resp = await client.get("/admin/billing/margins/summary")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_usage_financials_requires_auth(client):
    resp = await client.get("/admin/billing/usage-financials")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_simulate_pricing_requires_auth(client):
    resp = await client.post("/admin/billing/pricing/simulate", json={"provider": "local"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_simulate_pricing(client):
    resp = await _post("/admin/billing/pricing/simulate", {"provider": "local", "prompt_tokens": 100, "completion_tokens": 50}, client)
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "provider_cost_usd" in data
    assert "customer_price_brl" in data
    assert "gross_profit_brl" in data


@pytest.mark.asyncio
async def test_simulate_pricing_with_cache(client):
    no_cache = await _post("/admin/billing/pricing/simulate", {"provider": "local", "prompt_tokens": 100, "completion_tokens": 50, "cache_hit": False, "plan_code": "basic"}, client)
    cached = await _post("/admin/billing/pricing/simulate", {"provider": "local", "prompt_tokens": 100, "completion_tokens": 50, "cache_hit": True, "plan_code": "basic"}, client)
    assert no_cache.status_code == 200
    assert cached.status_code == 200
    assert cached.json()["customer_price_brl"] <= no_cache.json()["customer_price_brl"]


@pytest.mark.asyncio
async def test_simulate_all_providers(client):
    for provider in ["local", "lmstudio", "mock", "openai", "anthropic", "deepseek"]:
        resp = await _post("/admin/billing/pricing/simulate", {"provider": provider, "prompt_tokens": 100, "completion_tokens": 50}, client)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_margins_summary_response_format():
    from app.services.billing.pricing_engine import calculate_financials
    result = calculate_financials("local", 1000, 500, plan_code="basic")
    assert "gross_profit_brl" in result
    assert "margin_percent" in result
    assert "provider_cost_brl" in result
    assert "customer_price_brl" in result
