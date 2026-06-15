from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import timedelta

import httpx
import pytest
from app.api.commercial_revenue_escalations_admin import router as revenue_escalations_router
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import get_db_session
from app.models.commercial.commercial_revenue_alert_delivery import CommercialRevenueAlertDelivery
from app.models.commercial.commercial_revenue_escalation_policy import (
    CommercialRevenueEscalationPolicy,
)
from app.services.notifications.revenue_escalations import (
    apply_retry_backoff,
    deliver_webhook,
    evaluate_escalation_policies,
    retry_alert_delivery,
    sanitize_alert_payload,
)
from fastapi import FastAPI
from sqlalchemy import select


@pytest.fixture(autouse=True)
def revenue_escalations_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATIONS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATIONS_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "")
    monkeypatch.setenv("COMMERCIAL_REVENUE_SLACK_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REVENUE_SLACK_WEBHOOK_URL", "")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PAGERDUTY_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PAGERDUTY_ROUTING_KEY", "")
    monkeypatch.setenv("COMMERCIAL_REVENUE_EMAIL_ESCALATION_ENABLED", "false")
    monkeypatch.setenv("COMMERCIAL_REVENUE_EMAIL_ESCALATION_RECIPIENTS", "")
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATION_COOLDOWN_MINUTES", "30")
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATION_MAX_RETRIES", "3")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com,finance@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_FROM", "reports@example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _policy(**overrides) -> CommercialRevenueEscalationPolicy:
    data = {
        "name": "critical alerts",
        "enabled": True,
        "severity_threshold": "high",
        "trigger_types_json": [
            "manual_test",
            "critical_anomaly",
            "repeated_mismatches",
            "mass_disputes",
            "repeated_safe_mode_activations",
            "failed_revenue_protection_action",
        ],
        "allowed_delivery_types_json": ["webhook"],
        "cooldown_minutes": 30,
        "max_retries": 2,
        "escalation_order_json": ["webhook"],
        "metadata_json": {"authorization": "Bearer secret-value", "prompt": "hidden"},
    }
    data.update(overrides)
    return CommercialRevenueEscalationPolicy(**data)


class _FakeResponse:
    def __init__(self, status_code: int = 202, text: str = "ok"):
        self.status_code = status_code
        self.text = text


class _CapturingAsyncClient:
    calls: list[dict] = []
    raise_error: bool = False

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        type(self).calls.append({"url": url, "json": json, "headers": headers or {}})
        if type(self).raise_error:
            raise httpx.ConnectError("boom")
        return _FakeResponse()


@pytest.mark.asyncio
async def test_webhook_dry_run(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "https://hooks.example.com/revenue")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "top-secret-signing-key")
    get_settings.cache_clear()
    session.add(_policy())
    await session.commit()

    result = await evaluate_escalation_policies(
        session,
        source_type="policy_action",
        source_id="source-1",
        severity="critical",
        summary="manual test",
        recommendation="check dry-run",
        trigger_type="manual_test",
    )

    assert result["deliveries"][0]["status"] == "dry_run"
    row = (await session.execute(select(CommercialRevenueAlertDelivery))).scalar_one()
    assert row.status == "dry_run"
    assert row.destination == "https://h***.example.com..."
    assert "top-secret-signing-key" not in (row.response_summary or "")


@pytest.mark.asyncio
async def test_slack_disabled_is_suppressed(session):
    session.add(_policy(allowed_delivery_types_json=["slack"], escalation_order_json=["slack"]))
    await session.commit()

    result = await evaluate_escalation_policies(
        session,
        source_type="anomaly",
        source_id="source-2",
        severity="critical",
        summary="critical anomaly",
        trigger_type="critical_anomaly",
    )

    assert result["deliveries"][0]["status"] == "suppressed"


@pytest.mark.asyncio
async def test_pagerduty_disabled_is_suppressed(session):
    session.add(
        _policy(allowed_delivery_types_json=["pagerduty"], escalation_order_json=["pagerduty"])
    )
    await session.commit()

    result = await evaluate_escalation_policies(
        session,
        source_type="reconciliation",
        source_id="source-3",
        severity="high",
        summary="repeated mismatches",
        trigger_type="repeated_mismatches",
    )

    assert result["deliveries"][0]["status"] == "suppressed"


@pytest.mark.asyncio
async def test_email_escalation_dry_run(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_EMAIL_ESCALATION_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_EMAIL_ESCALATION_RECIPIENTS", "ops@example.com")
    get_settings.cache_clear()
    session.add(_policy(allowed_delivery_types_json=["email"], escalation_order_json=["email"]))
    await session.commit()

    result = await evaluate_escalation_policies(
        session,
        source_type="dispute",
        source_id="source-4",
        severity="high",
        summary="mass disputes",
        trigger_type="mass_disputes",
    )

    assert result["deliveries"][0]["status"] == "dry_run"
    row = (await session.execute(select(CommercialRevenueAlertDelivery))).scalar_one()
    assert row.destination == "o***@example.com"


@pytest.mark.asyncio
async def test_dedupe(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "https://hooks.example.com/revenue")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "dedupe-secret")
    get_settings.cache_clear()
    session.add(_policy())
    await session.commit()

    for _ in range(2):
        await evaluate_escalation_policies(
            session,
            source_type="policy_action",
            source_id="source-5",
            severity="critical",
            summary="same summary",
            trigger_type="manual_test",
        )

    rows = (
        (
            await session.execute(
                select(CommercialRevenueAlertDelivery).order_by(
                    CommercialRevenueAlertDelivery.created_at.asc()
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows[0].status == "dry_run"
    assert rows[1].status == "deduplicated"


@pytest.mark.asyncio
async def test_cooldown_suppression(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "https://hooks.example.com/revenue")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "cooldown-secret")
    get_settings.cache_clear()
    session.add(_policy())
    await session.commit()

    await evaluate_escalation_policies(
        session,
        source_type="policy_action",
        source_id="source-6",
        severity="critical",
        summary="summary-a",
        trigger_type="manual_test",
    )
    await evaluate_escalation_policies(
        session,
        source_type="policy_action",
        source_id="source-6",
        severity="critical",
        summary="summary-b",
        trigger_type="manual_test",
    )

    rows = (
        (
            await session.execute(
                select(CommercialRevenueAlertDelivery).order_by(
                    CommercialRevenueAlertDelivery.created_at.asc()
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows[0].status == "dry_run"
    assert rows[1].status == "suppressed"


def test_retry_backoff():
    assert apply_retry_backoff(0) == 30
    assert apply_retry_backoff(1) == 60
    assert apply_retry_backoff(2) == 120


@pytest.mark.asyncio
async def test_hmac_signing(monkeypatch: pytest.MonkeyPatch):
    _CapturingAsyncClient.calls = []
    _CapturingAsyncClient.raise_error = False
    monkeypatch.setattr(
        "app.services.notifications.revenue_escalations.httpx.AsyncClient", _CapturingAsyncClient
    )
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "https://hooks.example.com/revenue")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "signing-secret")
    get_settings.cache_clear()
    payload = {
        "source_type": "policy_action",
        "source_id": "abc",
        "trigger_type": "manual_test",
        "severity": "critical",
        "summary": "x",
        "recommendation": "y",
        "timestamp": utc_now().isoformat(),
        "metadata": {},
    }

    await deliver_webhook(payload, max_retries=0)

    headers = _CapturingAsyncClient.calls[0]["headers"]
    timestamp = headers["X-Commercial-Revenue-Timestamp"]
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    expected = hmac.new(
        b"signing-secret", f"{timestamp}.{body}".encode(), hashlib.sha256
    ).hexdigest()
    assert headers["X-Commercial-Revenue-Signature"] == f"v1={expected}"


def test_payload_sanitization():
    payload = sanitize_alert_payload(
        {
            "summary": "ok",
            "api_key": "sk-secret-123456789",
            "metadata": {"prompt": "hidden prompt", "response": "hidden response"},
            "message": "Authorization: Bearer top-secret-token",
        }
    )
    assert payload["api_key"] == "[REDACTED]"
    assert payload["metadata"]["prompt"] == "[REDACTED]"
    assert payload["metadata"]["response"] == "[REDACTED]"
    assert "top-secret-token" not in payload["message"]


@pytest.mark.asyncio
async def test_endpoints_require_admin_auth(session, app_client_factory):
    app = FastAPI()
    app.include_router(revenue_escalations_router)

    async def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = await app_client_factory(app)
    try:
        random_id = str(uuid.uuid4())
        assert (
            await client.get("/admin/billing/revenue-escalations/deliveries")
        ).status_code == 401
        assert (await client.get("/admin/billing/revenue-escalations/policies")).status_code == 401
        assert (
            await client.post("/admin/billing/revenue-escalations/test", json={})
        ).status_code == 401
        assert (
            await client.post(f"/admin/billing/revenue-escalations/retry/{random_id}")
        ).status_code == 401
        assert (await client.get("/admin/billing/revenue-escalations/status")).status_code == 401
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_failed_delivery_and_retry_success(session, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATIONS_MODE", "enabled")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "https://hooks.example.com/revenue")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "retry-secret")
    get_settings.cache_clear()
    session.add(_policy())
    await session.commit()

    _CapturingAsyncClient.calls = []
    _CapturingAsyncClient.raise_error = True
    monkeypatch.setattr(
        "app.services.notifications.revenue_escalations.httpx.AsyncClient", _CapturingAsyncClient
    )

    await evaluate_escalation_policies(
        session,
        source_type="policy_action",
        source_id="source-7",
        severity="critical",
        summary="failure then retry",
        trigger_type="manual_test",
    )

    delivery = (await session.execute(select(CommercialRevenueAlertDelivery))).scalar_one()
    assert delivery.status == "failed"

    _CapturingAsyncClient.raise_error = False
    delivery.last_retry_at = utc_now() - timedelta(hours=1)
    await session.commit()

    retried = await retry_alert_delivery(session, delivery.id)
    assert retried.status == "sent"
    assert retried.retry_count == 1
