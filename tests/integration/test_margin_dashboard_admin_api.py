from datetime import datetime, timezone

import pytest
from app.models.core.client import Client
from app.models.billing.request_financial import RequestFinancial
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_margin_dashboard_empty(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/financials/margin-dashboard", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["revenue_today_brl"] == 0.0
    assert data["cost_today_brl"] == 0.0
    assert data["requests_today"] == 0
    assert isinstance(data["requests_by_provider"], list)
    assert isinstance(data["clients_with_negative_margin"], list)

@pytest.mark.asyncio
async def test_margin_dashboard_no_leaks(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/financials/margin-dashboard", headers=admin_token_headers)
    assert response.status_code == 200
    data_str = response.text
    
    # Ensure no secrets leak
    assert "api_key" not in data_str.lower()
    assert "sk-" not in data_str
    assert "prompt" not in data_str.lower()
    assert "completion" not in data_str.lower()
    
    data = response.json()
    # Ensure schema matches what's expected without sensitive fields
    assert "generated_at_utc" in data
    assert "revenue_today_brl" in data
    assert "cost_by_provider" in data


@pytest.mark.asyncio
async def test_margin_dashboard_aggregates_current_day(
    admin_client: AsyncClient,
    admin_token_headers: dict,
):
    from app.db.session import get_db_session
    from app.main import app

    session_generator = app.dependency_overrides[get_db_session]()
    session = await session_generator.__anext__()
    try:
        client = Client(name="margin-dashboard-client")
        loss_client = Client(name="margin-dashboard-loss-client")
        session.add_all([client, loss_client])
        await session.flush()

        now = datetime.now(timezone.utc)
        session.add_all(
            [
                RequestFinancial(
                    client_id=str(client.id),
                    provider="local",
                    model="model-a",
                    customer_price_brl=10.0,
                    provider_cost_brl=4.0,
                    gross_profit_brl=6.0,
                    cache_hit=False,
                    created_at=now,
                ),
                RequestFinancial(
                    client_id=str(loss_client.id),
                    provider="local",
                    model="model-c",
                    customer_price_brl=3.0,
                    provider_cost_brl=8.0,
                    gross_profit_brl=-5.0,
                    cache_hit=False,
                    created_at=now,
                ),
                RequestFinancial(
                    client_id=str(client.id),
                    provider="openai",
                    model="model-b",
                    customer_price_brl=5.0,
                    provider_cost_brl=7.0,
                    gross_profit_brl=-2.0,
                    cache_hit=True,
                    created_at=now,
                ),
            ]
        )
        await session.commit()
    finally:
        await session_generator.aclose()

    response = await admin_client.get("/admin/financials/margin-dashboard", headers=admin_token_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["revenue_today_brl"] == 18.0
    assert data["cost_today_brl"] == 19.0
    assert data["gross_margin_today_brl"] == -1.0
    assert data["gross_margin_percent_today"] == pytest.approx(-5.5555, rel=1e-3)
    assert data["requests_today"] == 3
    assert data["cache_hit_rate_today"] == pytest.approx(33.3333, rel=1e-3)
    assert data["estimated_cache_savings_brl"] == 9.5
    assert [entry["provider"] for entry in data["cost_by_provider"]] == ["local", "openai"]
    assert data["top_expensive_models"][0]["model"] == "model-c"
    assert data["clients_with_negative_margin"][0]["client_id"] == str(loss_client.id)
