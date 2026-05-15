from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from fastapi import FastAPI

from app.core.config import get_settings
from app.api.commercial_revenue_protection_admin import router as revenue_protection_router
from app.db.session import get_db_session
from app.models.client import Client
from app.models.commercial_financial_anomaly import CommercialFinancialAnomaly
from app.models.commercial_revenue_protection_action import CommercialRevenueProtectionAction
from app.models.commercial_revenue_protection_policy import CommercialRevenueProtectionPolicy
from app.services.billing.revenue_protection import (
    apply_action,
    evaluate_revenue_protection_policies,
    get_active_revenue_protection_constraints,
    match_anomaly_to_policy,
    revert_action,
)
from app.services.notifications.revenue_alerts import send_revenue_alert
from app.services.routing.commercial_routing import simulate_commercial_routing
from app.schemas.routing import CommercialSimulateRequest, TaskType


@pytest.fixture(autouse=True)
def revenue_protection_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_MODE", "report_only")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE", "false")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_COOLDOWN_MINUTES", "60")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _seed_client_and_anomaly(session, anomaly_type: str = "cost_spike", severity: str = "critical", model: str | None = "gpt-expensive"):
    client = Client(name=f"rp-client-{uuid.uuid4()}")
    session.add(client)
    await session.flush()
    anomaly = CommercialFinancialAnomaly(
        anomaly_type=anomaly_type,
        severity=severity,
        client_id=client.id,
        provider="openai",
        model=model,
        status="open",
        deviation_percent=150.0,
        z_score=7.0,
        explanation="sk-secret prompt should not leak",
        metadata_json={"qos_tier": "Premium", "api_key": "sk-secret", "prompt": "secret prompt"},
    )
    session.add(anomaly)
    await session.commit()
    return client, anomaly


def _policy(**overrides) -> CommercialRevenueProtectionPolicy:
    data = {
        "name": "protect margin",
        "enabled": True,
        "trigger_type": "cost_spike",
        "severity_threshold": "high",
        "action_type": "safe_mode",
        "scope_type": "client",
        "scope_identifier": None,
        "mode": "report_only",
        "cooldown_minutes": 60,
        "metadata_json": {"api_key": "sk-secret", "prompt": "hide me"},
    }
    data.update(overrides)
    return CommercialRevenueProtectionPolicy(**data)


@pytest.mark.asyncio
async def test_policy_match_by_anomaly(session):
    client, anomaly = await _seed_client_and_anomaly(session)
    policy = _policy(scope_identifier=str(client.id))
    assert match_anomaly_to_policy(anomaly, policy) is True


@pytest.mark.asyncio
async def test_report_only_creates_proposed(session):
    client, anomaly = await _seed_client_and_anomaly(session)
    session.add(_policy(scope_identifier=str(client.id), mode="report_only"))
    await session.commit()

    result = await evaluate_revenue_protection_policies(session)
    assert result["proposed"] == 1

    actions = (await session.execute(select(CommercialRevenueProtectionAction))).scalars().all()
    assert any(row.status == "proposed" for row in actions)


@pytest.mark.asyncio
async def test_approval_required_creates_pending_approval(session):
    client, anomaly = await _seed_client_and_anomaly(session)
    session.add(_policy(scope_identifier=str(client.id), mode="approval_required"))
    await session.commit()

    await evaluate_revenue_protection_policies(session)
    rows = (await session.execute(select(CommercialRevenueProtectionAction))).scalars().all()
    assert any(row.status == "pending_approval" for row in rows)


@pytest.mark.asyncio
async def test_enforce_blocked_if_allow_enforce_false(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_MODE", "enforce")
    get_settings.cache_clear()
    client, anomaly = await _seed_client_and_anomaly(session)
    session.add(_policy(scope_identifier=str(client.id), mode="enforce"))
    await session.commit()

    await evaluate_revenue_protection_policies(session)
    action = (await session.execute(select(CommercialRevenueProtectionAction))).scalars().first()
    assert action.status == "blocked"


@pytest.mark.asyncio
async def test_safe_mode_generates_constraint_and_revert_removes_it(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_MODE", "enforce")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE", "true")
    get_settings.cache_clear()
    client, anomaly = await _seed_client_and_anomaly(session)
    policy = _policy(scope_identifier=str(client.id), mode="enforce", action_type="safe_mode")
    session.add(policy)
    await session.commit()

    await evaluate_revenue_protection_policies(session)
    action = (await session.execute(select(CommercialRevenueProtectionAction))).scalars().first()
    live_action = await session.get(CommercialRevenueProtectionAction, action.id)
    constraints = get_active_revenue_protection_constraints(client_id=client.id)
    assert constraints["safe_mode"] is True
    assert constraints["force_local_only"] is True

    await revert_action(session, live_action)
    reverted = get_active_revenue_protection_constraints(client_id=client.id)
    assert reverted["safe_mode"] is False
    assert reverted["force_local_only"] is False


@pytest.mark.asyncio
async def test_restrict_expensive_models_generates_constraint(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_MODE", "enforce")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE", "true")
    get_settings.cache_clear()
    client, anomaly = await _seed_client_and_anomaly(session, model="gpt-expensive")
    session.add(_policy(scope_identifier="gpt-expensive", scope_type="model", mode="enforce", action_type="restrict_expensive_models"))
    await session.commit()

    await evaluate_revenue_protection_policies(session)
    constraints = get_active_revenue_protection_constraints(client_id=client.id, model="gpt-expensive")
    assert "gpt-expensive" in constraints["restricted_models"]


@pytest.mark.asyncio
async def test_force_local_only_feeds_routing_helper(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_MODE", "enforce")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE", "true")
    monkeypatch.setenv("CLOUD_PROVIDERS_ENABLED", "true")
    get_settings.cache_clear()
    client, anomaly = await _seed_client_and_anomaly(session)
    session.add(_policy(scope_identifier=str(client.id), mode="enforce", action_type="force_local_only"))
    await session.commit()

    await evaluate_revenue_protection_policies(session)
    result = simulate_commercial_routing(
        CommercialSimulateRequest(
            client_id=str(client.id),
            plan="basic",
            model="default",
            task_type=TaskType.general,
            cloud_allowed=True,
        )
    )
    assert "force_local_only" in result.explanation
    assert result.selected_route is None or result.selected_route.provider in {"local", "lmstudio", "mock"}


@pytest.mark.asyncio
async def test_cooldown_prevents_repetition(session):
    client, anomaly = await _seed_client_and_anomaly(session)
    session.add(_policy(scope_identifier=str(client.id), mode="report_only", cooldown_minutes=60))
    await session.commit()

    await evaluate_revenue_protection_policies(session)
    await evaluate_revenue_protection_policies(session)
    rows = (await session.execute(select(CommercialRevenueProtectionAction))).scalars().all()
    assert any(row.status == "skipped" for row in rows)


@pytest.mark.asyncio
async def test_webhook_disabled_and_dry_run(monkeypatch: pytest.MonkeyPatch):
    disabled = await send_revenue_alert({"api_key": "sk-secret", "message": "hello"})
    assert disabled["status"] == "internal_only"
    assert "sk-secret" not in str(disabled["payload"])

    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_WEBHOOK_ENABLED", "true")
    get_settings.cache_clear()
    dry_run = await send_revenue_alert({"authorization": "Bearer sk-secret"})
    assert dry_run["status"] == "dry_run"
    assert "sk-secret" not in str(dry_run["payload"])


@pytest.mark.asyncio
async def test_endpoints_require_admin_auth(session, app_client_factory):
    app = FastAPI()
    app.include_router(revenue_protection_router)

    async def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = await app_client_factory(app)
    try:
        assert (await client.get("/admin/billing/revenue-protection/policies")).status_code == 401
        assert (await client.post("/admin/billing/revenue-protection/evaluate", json={"anomaly_ids": []})).status_code == 401
        assert (await client.get("/admin/billing/revenue-protection/status")).status_code == 401
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_admin_endpoints_and_sanitized_payload(session, app_client_factory, admin_token_headers):
    app = FastAPI()
    app.include_router(revenue_protection_router)

    async def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = await app_client_factory(app)
    create_resp = await client.post(
        "/admin/billing/revenue-protection/policies",
        headers=admin_token_headers,
        json={
            "name": "sanitize policy",
            "enabled": True,
            "trigger_type": "cost_spike",
            "severity_threshold": "high",
            "action_type": "notify",
            "scope_type": "global",
            "scope_identifier": None,
            "mode": "report_only",
            "cooldown_minutes": 60,
            "metadata_json": {"api_key": "sk-secret", "prompt": "hide me"},
        },
    )
    assert create_resp.status_code == 201
    assert "sk-secret" not in create_resp.text

    list_resp = await client.get("/admin/billing/revenue-protection/policies", headers=admin_token_headers)
    try:
        assert list_resp.status_code == 200
        assert "sk-secret" not in list_resp.text
        assert "[REDACTED]" in list_resp.text
    finally:
        await client.aclose()
