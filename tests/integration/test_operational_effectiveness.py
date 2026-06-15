from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date, timedelta

import httpx
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.security import hash_secret, short_prefix
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.commercial.commercial_compliance import (
    CommercialControlAttestation,
    CommercialControlException,
    CommercialControlPolicy,
)
from app.models.commercial.commercial_financial_reconciliation import (
    CommercialFinancialReconciliation,
)
from app.models.commercial.commercial_revenue_alert_delivery import CommercialRevenueAlertDelivery
from app.models.commercial.commercial_revenue_escalation_policy import (
    CommercialRevenueEscalationPolicy,
)
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.services.compliance.operational_controls import (
    add_operational_evidence,
    calculate_effectiveness_score,
    create_control,
    detect_overdue_reviews,
    evaluate_control_effectiveness,
    link_exception,
    summarize_operational_controls,
)
from sqlalchemy import select


@pytest.fixture(autouse=True)
def operational_effectiveness_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_OPERATIONAL_CONTROLS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_OPERATIONAL_CONTROLS_MODE", "report_only")
    monkeypatch.setenv("COMMERCIAL_OPERATIONAL_CONTROL_OVERDUE_ESCALATIONS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATIONS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_ESCALATIONS_MODE", "dry_run")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_URL", "https://hooks.example.com/revenue")
    monkeypatch.setenv("COMMERCIAL_REVENUE_WEBHOOK_SIGNING_SECRET", "test-signing-secret")
    monkeypatch.setenv("COMMERCIAL_REVENUE_EMAIL_ESCALATION_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_EMAIL_ESCALATION_RECIPIENTS", "ops@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_EMAIL_ALLOWLIST", "ops@example.com")
    monkeypatch.setenv("COMMERCIAL_REPORT_SMTP_FROM", "reports@example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def operational_portal_client(session, fake_redis) -> AsyncIterator[httpx.AsyncClient]:
    async def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def _create_portal_client(session) -> tuple[Client, str]:
    client = Client(
        name="Operational Portal Client",
        billing_status="active",
        is_blocked=False,
        metadata_json=json.dumps(
            {
                "contact_email": "portal@example.com",
                "enterprise_portal_roles": ["enterprise_auditor"],
            }
        ),
    )
    session.add(client)
    await session.flush()
    plaintext = "sk-operational-portal"
    api_key = ApiKey(
        client_id=client.id,
        name="Portal Key",
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps(["enterprise_auditor"]),
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    return client, plaintext


@pytest.mark.asyncio
async def test_effectiveness_score_and_status(session):
    control = await create_control(
        session,
        control_code="OPS-EFF-001",
        name="Revenue reconciliation monitoring",
        category="financial",
        review_frequency="quarterly",
        evidence_sla_days=7,
    )
    await session.flush()

    evidence = await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="reconciliation",
        title="Old mismatch export",
    )
    evidence.collected_at = evidence.created_at - timedelta(days=12)

    exception = CommercialControlException(
        exception_type="control_gap",
        severity="high",
        status="open",
        description="linked exception",
        owner="owner@example.com",
    )
    session.add(exception)
    policy = CommercialControlPolicy(
        name="Linked policy",
        control_area="financial",
        action_type="manual_review",
        requires_approval=False,
        evidence_required=True,
        segregation_required=True,
        review_frequency="quarterly",
    )
    session.add(policy)
    await session.flush()
    await link_exception(
        session,
        control_id=control.id,
        exception_id=exception.id,
        linkage_reason="Customer-visible gap",
    )

    attestation = CommercialControlAttestation(
        control_policy_id=policy.id,
        attestation_period_start=date(2026, 1, 1),
        attestation_period_end=date(2026, 3, 31),
        attested_by="reviewer",
        status="failed",
    )
    session.add(attestation)
    session.add(
        CommercialFinancialReconciliation(
            reconciliation_type="invoice",
            period_start=evidence.created_at - timedelta(days=1),
            period_end=evidence.created_at,
            expected_amount_brl=10,
            actual_amount_brl=5,
            delta_amount_brl=-5,
            discrepancy_percent=50,
            status="mismatch",
        )
    )
    await session.commit()

    await detect_overdue_reviews(
        session, control_id=control.id, as_of=evidence.created_at + timedelta(days=120)
    )
    scored = await evaluate_control_effectiveness(session, control.id)
    await session.commit()

    assert await calculate_effectiveness_score(session, control.id) < 50
    assert scored.effectiveness_status == "ineffective"


@pytest.mark.asyncio
async def test_escalation_integration(session):
    session.add(
        CommercialRevenueEscalationPolicy(
            name="operational overdue",
            enabled=True,
            severity_threshold="high",
            trigger_types_json=[
                "overdue_review",
                "stale_evidence",
                "ineffective_control",
                "repeated_exceptions",
            ],
            allowed_delivery_types_json=["webhook", "email"],
            escalation_order_json=["webhook", "email"],
            cooldown_minutes=0,
            max_retries=1,
        )
    )
    control = await create_control(
        session,
        control_code="OPS-EFF-002",
        name="Escalation coverage",
        category="operational",
        review_frequency="quarterly",
        evidence_sla_days=5,
    )
    evidence = await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="report",
        title="Expired evidence",
    )
    evidence.collected_at = evidence.created_at - timedelta(days=10)
    await session.commit()

    summary = await summarize_operational_controls(session)
    await session.commit()

    deliveries = (await session.execute(select(CommercialRevenueAlertDelivery))).scalars().all()
    assert summary["escalation_status"]
    assert deliveries
    assert {item.delivery_type for item in deliveries} == {"webhook", "email"}
    assert all(item.status == "dry_run" for item in deliveries)


@pytest.mark.asyncio
async def test_portal_visibility_is_tenant_scoped(session, operational_portal_client):
    tenant_client, api_key = await _create_portal_client(session)
    other_client = Client(name="Other Tenant", billing_status="active", is_blocked=False)
    session.add(other_client)
    await session.flush()

    control = await create_control(
        session,
        control_code="OPS-PORTAL-001",
        name="Portal-visible control",
        category="security",
        review_frequency="quarterly",
    )
    await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="audit_log",
        title="Portal evidence",
    )
    tenant_exception = CommercialControlException(
        client_id=tenant_client.id,
        exception_type="tenant_gap",
        severity="high",
        status="open",
        description="tenant linked",
    )
    other_exception = CommercialControlException(
        client_id=other_client.id,
        exception_type="other_gap",
        severity="high",
        status="open",
        description="other linked",
    )
    session.add_all([tenant_exception, other_exception])
    await session.flush()
    await link_exception(
        session, control_id=control.id, exception_id=tenant_exception.id, linkage_reason="tenant"
    )
    await link_exception(
        session, control_id=control.id, exception_id=other_exception.id, linkage_reason="other"
    )
    await session.commit()

    controls_resp = await operational_portal_client.get(
        "/portal/audit/operational-controls",
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Portal-Actor-Email": "portal@example.com",
        },
    )
    evidence_resp = await operational_portal_client.get(
        "/portal/audit/operational-evidence",
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Portal-Actor-Email": "portal@example.com",
        },
    )
    reviews_resp = await operational_portal_client.get(
        "/portal/audit/operational-reviews",
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Portal-Actor-Email": "portal@example.com",
        },
    )
    assert controls_resp.status_code == 200
    assert evidence_resp.status_code == 200
    assert reviews_resp.status_code == 200
    assert len(controls_resp.json()["items"]) == 1
    assert controls_resp.json()["items"][0]["linked_exceptions"][0]["exception_id"] == str(
        tenant_exception.id
    )
    assert len(evidence_resp.json()["items"]) == 1
    assert len(reviews_resp.json()["items"]) == 1
