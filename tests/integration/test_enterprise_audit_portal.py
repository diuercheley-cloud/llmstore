from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date

import httpx
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.security import hash_secret, short_prefix
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.core.api_key import ApiKey
from app.models.billing.billing_invoice import BillingInvoice
from app.models.core.client import Client
from app.models.commercial.commercial_billing_dispute import CommercialBillingDispute
from app.models.commercial.commercial_compliance import CommercialControlPolicy
from app.models.commercial.commercial_financial_audit_event import CommercialFinancialAuditEvent
from app.models.commercial.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.services.compliance.financial_controls import (
    create_attestation,
    create_evidence_package,
    open_exception,
    require_approval_chain,
)
from app.services.compliance.operational_controls import (
    add_operational_evidence,
    create_control,
    link_exception,
)


@pytest.fixture(autouse=True)
def enterprise_audit_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_ENTERPRISE_AUDIT_PORTAL_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_ENTERPRISE_AUDIT_REQUIRE_RBAC", "true")
    monkeypatch.setenv("COMMERCIAL_ENTERPRISE_AUDIT_EXPORT_PDF_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def portal_http_client(session, fake_redis) -> AsyncIterator[httpx.AsyncClient]:
    async def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


async def _create_client_and_key(session, *, name: str, scopes: list[str], metadata: dict | None = None) -> tuple[Client, str]:
    client = Client(
        name=name,
        billing_status="active",
        is_blocked=False,
        metadata_json=json.dumps(metadata or {"contact_email": f"{name.lower()}@example.com"}),
    )
    session.add(client)
    await session.flush()
    plaintext = f"sk-{name.lower().replace(' ', '-')}-portal-key"
    api_key = ApiKey(
        client_id=client.id,
        name=f"{name} Key",
        key_prefix=short_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes_json=json.dumps(scopes),
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    return client, plaintext


async def _seed_portal_data(session, client: Client) -> None:
    policy = CommercialControlPolicy(
        name="Tenant approval control",
        control_area="billing",
        action_type="manual_credit",
        requires_approval=True,
        evidence_required=True,
        segregation_required=True,
        review_frequency="quarterly",
    )
    session.add(policy)
    await session.flush()
    evidence = await create_evidence_package(
        session,
        client_id=client.id,
        package_type="billing",
        target_type="invoice",
        target_id="inv-001",
        summary="Evidence for tenant export",
        actor="alice",
        payload={"prompt": "do not expose", "api_key": "TEST_API_KEY"},
        before_state={"status": "draft"},
        after_state={"status": "approved"},
    )
    await require_approval_chain(
        session,
        client_id=client.id,
        policy=policy,
        target_type="invoice",
        target_id="inv-001",
        requested_by="alice",
        evidence_package_id=evidence.id,
    )
    await create_attestation(
        session,
        client_id=client.id,
        control_policy_id=policy.id,
        attested_by="alice",
        attestation_period_start=date(2026, 1, 1),
        attestation_period_end=date(2026, 3, 31),
        status="attested",
        notes="clean attestation",
        evidence_package_id=evidence.id,
    )
    exception = await open_exception(
        session,
        client_id=client.id,
        control_policy_id=policy.id,
        exception_type="late_evidence",
        severity="high",
        description="Temporary exception",
        owner="alice",
    )
    operational_control = await create_control(
        session,
        control_code=f"OPS-{str(client.id)[:8]}",
        name="Tenant operational control",
        category="security",
        owner_email="alice@example.com",
        review_frequency="quarterly",
    )
    await add_operational_evidence(
        session,
        control_id=operational_control.id,
        evidence_type="audit_log",
        title="Operational evidence",
        summary="Evidence for operational control",
        evidence_json={"secret": "must-drop", "result": "ok"},
    )
    await link_exception(
        session,
        control_id=operational_control.id,
        exception_id=exception.id,
        linkage_reason="Tenant-visible operational gap",
    )
    session.add(
        CommercialFinancialAuditEvent(
            event_type="manual_credit",
            client_id=client.id,
            related_record_type="invoice",
            related_record_id="inv-001",
            amount_brl=12.34,
            metadata_json={"api_key": "sk-leak", "notes": "safe"},
            immutable_hash="a" * 64,
        )
    )
    session.add(
        CommercialBillingDispute(
            client_id=client.id,
            dispute_type="invoice_amount",
            status="open",
            claimed_amount_brl=10,
            disputed_reason="Unexpected line item",
        )
    )
    session.add(
        CommercialQoSBillingRecord(
            client_id=client.id,
            qos_tier="enterprise",
            model="default",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 1),
            compute_seconds=5,
            priority_slots_consumed=2,
            estimated_internal_cost_brl=1,
            opportunity_cost_brl=0,
            billable_amount_brl=3,
            billing_mode="invoiced",
            status="invoiced",
            idempotency_key=f"qos-{client.id}",
        )
    )
    session.add(
        BillingInvoice(
            client_id=client.id,
            status="pending",
            currency="BRL",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            monthly_price=100,
            included_tokens=1000,
            used_tokens=900,
            overage_tokens=0,
            overage_price_per_1k_tokens=0,
            overage_cost=0,
            total_amount=100,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_enterprise_audit_portal_flow_and_sanitized_download(portal_http_client, session):
    client_a, key_a = await _create_client_and_key(session, name="Client A", scopes=["enterprise_auditor"])
    client_b, key_b = await _create_client_and_key(session, name="Client B", scopes=["enterprise_auditor"])
    await _seed_portal_data(session, client_a)
    await _seed_portal_data(session, client_b)

    approval_resp = await portal_http_client.get(
        "/portal/audit/approval-chains",
        headers={"Authorization": f"Bearer {key_a}", "User-Agent": "audit-agent secret=sk-unsafe", "X-Portal-Actor-Email": "alice@example.com"},
    )
    assert approval_resp.status_code == 200
    approval_items = approval_resp.json()["items"]
    assert len(approval_items) == 1
    assert approval_items[0]["client_id"] == str(client_a.id)

    operational_controls_resp = await portal_http_client.get(
        "/portal/audit/operational-controls",
        headers={"Authorization": f"Bearer {key_a}", "X-Portal-Actor-Email": "alice@example.com"},
    )
    assert operational_controls_resp.status_code == 200
    assert len(operational_controls_resp.json()["items"]) == 1

    operational_evidence_resp = await portal_http_client.get(
        "/portal/audit/operational-evidence",
        headers={"Authorization": f"Bearer {key_a}", "X-Portal-Actor-Email": "alice@example.com"},
    )
    assert operational_evidence_resp.status_code == 200
    assert len(operational_evidence_resp.json()["items"]) == 1

    operational_reviews_resp = await portal_http_client.get(
        "/portal/audit/operational-reviews",
        headers={"Authorization": f"Bearer {key_a}", "X-Portal-Actor-Email": "alice@example.com"},
    )
    assert operational_reviews_resp.status_code == 200
    assert len(operational_reviews_resp.json()["items"]) == 1

    generate_resp = await portal_http_client.post(
        "/portal/audit/reports/generate",
        headers={"Authorization": f"Bearer {key_a}", "X-Portal-Actor-Email": "alice@example.com"},
        json={
            "report_type": "audit",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "export_format": "json",
            "filters_json": {"status": "pending", "actor": "alice", "prompt": "do not keep"},
        },
    )
    assert generate_resp.status_code == 201
    report_payload = generate_resp.json()["report"]
    assert len(report_payload["immutable_hash"]) == 64
    assert generate_resp.json()["summary"]["operational_controls"] == 1
    assert generate_resp.json()["summary"]["operational_evidence"] == 1
    assert generate_resp.json()["summary"]["operational_reviews"] == 1

    reports_resp = await portal_http_client.get(
        "/portal/audit/reports",
        headers={"Authorization": f"Bearer {key_a}"},
    )
    assert reports_resp.status_code == 200
    reports = reports_resp.json()["items"]
    assert len(reports) == 1
    assert reports[0]["report_type"] == "audit"

    download_resp = await portal_http_client.get(
        f"/portal/audit/reports/{report_payload['id']}/download",
        headers={"Authorization": f"Bearer {key_a}", "X-Portal-Actor-Email": "alice@example.com"},
    )
    assert download_resp.status_code == 200
    body = download_resp.text
    assert "CONFIDENTIAL ENTERPRISE AUDIT EXPORT" in body
    assert "TEST_API_KEY" not in body
    assert "sk-leak" not in body
    assert '"prompt"' not in body

    cross_tenant_resp = await portal_http_client.get(
        f"/portal/audit/reports/{report_payload['id']}/download",
        headers={"Authorization": f"Bearer {key_b}"},
    )
    assert cross_tenant_resp.status_code == 404

    logs_resp = await portal_http_client.get(
        "/portal/audit/access-logs",
        headers={"Authorization": f"Bearer {key_a}", "X-Portal-Actor-Email": "alice@example.com"},
    )
    assert logs_resp.status_code == 200
    actions = {item["action"] for item in logs_resp.json()["items"]}
    assert {"view", "export", "download"}.issubset(actions)
    assert any(item["ip_masked"] for item in logs_resp.json()["items"])
    assert all("sk-unsafe" not in (item["user_agent_sanitized"] or "") for item in logs_resp.json()["items"])


@pytest.mark.asyncio
async def test_enterprise_audit_endpoints_require_auth(portal_http_client):
    response = await portal_http_client.get("/portal/audit/approval-chains")
    assert response.status_code == 401
