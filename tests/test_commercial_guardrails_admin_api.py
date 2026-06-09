from datetime import datetime, timezone

import pytest
from app.models.client import Client
from app.models.request_financial import RequestFinancial
from app.services.commercial_guardrails import clear_commercial_guardrail_runtime_events
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def commercial_guardrails_env(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings

    monkeypatch.setenv("COMMERCIAL_GUARDRAILS_ENABLED", "false")
    monkeypatch.setenv("MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL", "0")
    monkeypatch.setenv("MAX_PROVIDER_COST_PER_DAY_BRL", "0")
    monkeypatch.setenv("MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL", "0")
    monkeypatch.setenv("MARGIN_WARNING_PERCENT", "20")
    monkeypatch.setenv("NEGATIVE_MARGIN_BLOCK_MODE", "report_only")
    monkeypatch.setenv("GLOBAL_CLOUD_KILL_SWITCH", "false")
    monkeypatch.setenv("CLOUD_PROVIDERS_ENABLED", "false")
    get_settings.cache_clear()
    clear_commercial_guardrail_runtime_events()
    yield
    clear_commercial_guardrail_runtime_events()
    get_settings.cache_clear()


def _apply_guardrail_env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    from app.core.config import get_settings

    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


async def _seed_financials(admin_client: AsyncClient, suffix: str = "base") -> tuple[str, str]:
    from app.db.session import get_db_session
    from app.main import app

    session_generator = app.dependency_overrides[get_db_session]()
    session = await session_generator.__anext__()
    try:
        client_a = Client(name=f"guardrails-client-{suffix}")
        client_b = Client(name=f"guardrails-loss-client-{suffix}")
        session.add_all([client_a, client_b])
        await session.flush()

        now = datetime.now(timezone.utc)
        session.add_all(
            [
                RequestFinancial(
                    client_id=str(client_a.id),
                    provider="openai",
                    model="gpt-4o-mini",
                    customer_price_brl=18.0,
                    provider_cost_brl=11.0,
                    gross_profit_brl=7.0,
                    cache_hit=False,
                    created_at=now,
                ),
                RequestFinancial(
                    client_id=str(client_b.id),
                    provider="openai",
                    model="gpt-4o-mini",
                    customer_price_brl=4.0,
                    provider_cost_brl=7.0,
                    gross_profit_brl=-3.0,
                    cache_hit=False,
                    created_at=now,
                ),
                RequestFinancial(
                    client_id=str(client_b.id),
                    provider="local",
                    model="gemma-local",
                    customer_price_brl=3.0,
                    provider_cost_brl=1.0,
                    gross_profit_brl=2.0,
                    cache_hit=True,
                    created_at=now,
                ),
            ]
        )
        await session.commit()
        return str(client_a.id), str(client_b.id)
    finally:
        await session_generator.aclose()


@pytest.mark.asyncio
async def test_commercial_guardrails_requires_admin_auth(admin_client: AsyncClient):
    overview = await admin_client.get("/admin/commercial-guardrails/overview")
    simulate = await admin_client.post("/admin/commercial-guardrails/simulate", json={
        "client_id": "00000000-0000-0000-0000-000000000001",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "estimated_cost_brl": 1.0,
        "estimated_revenue_brl": 2.0,
    })
    runtime = await admin_client.get("/admin/commercial-guardrails/runtime-status")
    assert overview.status_code == 401
    assert simulate.status_code == 401
    assert runtime.status_code == 401


@pytest.mark.asyncio
async def test_commercial_guardrails_overview_empty(admin_client: AsyncClient, admin_token_headers: dict):
    response = await admin_client.get("/admin/commercial-guardrails/overview", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "disabled"
    assert data["global_usage_today"]["global_provider_cost_today_brl"] == 0.0
    assert data["providers"] == []
    assert data["clients"] == []
    assert data["would_block"] == []

    runtime = await admin_client.get("/admin/commercial-guardrails/runtime-status", headers=admin_token_headers)
    assert runtime.status_code == 200
    assert runtime.json()["enforcement_mode"] == "disabled"
    assert runtime.json()["blocked_cloud_requests_today"] == 0


@pytest.mark.asyncio
async def test_commercial_guardrails_overview_populated_and_flags(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, admin_token_headers: dict):
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        MAX_PROVIDER_COST_PER_DAY_BRL="10",
        MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL="6",
        MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL="25",
        NEGATIVE_MARGIN_BLOCK_MODE="report_only",
    )
    client_a_id, client_b_id = await _seed_financials(admin_client, "populated")

    response = await admin_client.get("/admin/commercial-guardrails/overview", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "report_only"
    assert data["global_usage_today"]["global_provider_cost_today_brl"] == 19.0
    assert "openai" in data["providers_over_block_threshold"]
    assert client_b_id in data["clients_with_negative_margin"]
    assert client_b_id in data["clients_over_block_threshold"]
    assert any(item["type"] == "provider_daily_cost" and item["provider"] == "openai" for item in data["would_block"])
    assert any(item["type"] == "negative_margin" and item["client_id"] == client_b_id for item in data["would_block"])
    assert any(client["client_id"] == client_a_id for client in data["clients"])


@pytest.mark.asyncio
async def test_commercial_guardrails_simulate_positive_margin(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, admin_token_headers: dict):
    _apply_guardrail_env(monkeypatch, COMMERCIAL_GUARDRAILS_ENABLED="true")
    client_a_id, _ = await _seed_financials(admin_client, "simulate-positive")

    response = await admin_client.post(
        "/admin/commercial-guardrails/simulate",
        headers=admin_token_headers,
        json={
            "client_id": client_a_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "estimated_cost_brl": 1.25,
            "estimated_revenue_brl": 2.00,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_in_report_only"] is True
    assert data["would_allow_if_enforced"] is True
    assert data["estimated_margin_brl"] == 0.75
    assert data["estimated_margin_percent"] == 37.5
    assert data["reasons"] == []


@pytest.mark.asyncio
async def test_commercial_guardrails_simulate_negative_margin(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, admin_token_headers: dict):
    _apply_guardrail_env(monkeypatch, COMMERCIAL_GUARDRAILS_ENABLED="true")
    client_a_id, _ = await _seed_financials(admin_client, "simulate-negative")

    response = await admin_client.post(
        "/admin/commercial-guardrails/simulate",
        headers=admin_token_headers,
        json={
            "client_id": client_a_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "estimated_cost_brl": 10.0,
            "estimated_revenue_brl": 1.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_in_report_only"] is True
    assert data["would_allow_if_enforced"] is False
    assert "negative_margin" in data["reasons"]


@pytest.mark.asyncio
async def test_commercial_guardrails_simulate_above_daily_limit(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, admin_token_headers: dict):
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        MAX_PROVIDER_COST_PER_DAY_BRL="12",
        MAX_CLIENT_PROVIDER_COST_PER_DAY_BRL="20",
        MAX_GLOBAL_PROVIDER_COST_PER_DAY_BRL="50",
    )
    client_a_id, _ = await _seed_financials(admin_client, "simulate-limit")

    response = await admin_client.post(
        "/admin/commercial-guardrails/simulate",
        headers=admin_token_headers,
        json={
            "client_id": client_a_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "estimated_cost_brl": 2.0,
            "estimated_revenue_brl": 3.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["would_allow_if_enforced"] is False
    assert "provider_daily_cost_limit_exceeded" in data["reasons"]


@pytest.mark.asyncio
async def test_commercial_guardrails_payload_is_sanitized(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, admin_token_headers: dict):
    _apply_guardrail_env(monkeypatch, COMMERCIAL_GUARDRAILS_ENABLED="true")
    client_a_id, _ = await _seed_financials(admin_client, "sanitize")

    overview = await admin_client.get("/admin/commercial-guardrails/overview", headers=admin_token_headers)
    simulate = await admin_client.post(
        "/admin/commercial-guardrails/simulate",
        headers=admin_token_headers,
        json={
            "client_id": client_a_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "estimated_cost_brl": 1.0,
            "estimated_revenue_brl": 2.0,
        },
    )
    payload = overview.text + simulate.text
    assert "provider_api_key" not in payload.lower()
    assert "authorization" not in payload.lower()
    assert "prompt" not in payload.lower()
    assert "response complete" not in payload.lower()
    assert "sk-" not in payload


@pytest.mark.asyncio
async def test_commercial_guardrails_default_report_mode_does_not_block(monkeypatch: pytest.MonkeyPatch, admin_client: AsyncClient, admin_token_headers: dict):
    _apply_guardrail_env(
        monkeypatch,
        COMMERCIAL_GUARDRAILS_ENABLED="true",
        MAX_PROVIDER_COST_PER_DAY_BRL="10",
        NEGATIVE_MARGIN_BLOCK_MODE="report_only",
    )
    _, client_b_id = await _seed_financials(admin_client, "report-mode")

    overview = await admin_client.get("/admin/commercial-guardrails/overview", headers=admin_token_headers)
    simulate = await admin_client.post(
        "/admin/commercial-guardrails/simulate",
        headers=admin_token_headers,
        json={
            "client_id": client_b_id,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "estimated_cost_brl": 0.5,
            "estimated_revenue_brl": 0.25,
        },
    )
    assert overview.status_code == 200
    assert simulate.status_code == 200
    assert overview.json()["mode"] == "report_only"
    assert simulate.json()["allowed_in_report_only"] is True
