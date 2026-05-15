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
from app.models.api_key import ApiKey
from app.models.client import Client
from app.models.commercial_compliance import CommercialControlPolicy
from app.services.compliance.financial_controls import create_evidence_package, open_exception, require_approval_chain


@pytest.fixture(autouse=True)
def enterprise_audit_rbac_env(monkeypatch: pytest.MonkeyPatch):
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


async def _make_client_key(session, *, name: str, scopes: list[str]) -> tuple[Client, str]:
    client = Client(name=name, billing_status="active", is_blocked=False, metadata_json=json.dumps({"contact_email": f"{name}@example.com"}))
    session.add(client)
    await session.flush()
    plaintext = f"sk-{name}-key"
    session.add(
        ApiKey(
            client_id=client.id,
            name=f"{name} key",
            key_prefix=short_prefix(plaintext),
            key_hash=hash_secret(plaintext),
            scopes_json=json.dumps(scopes),
            is_active=True,
        )
    )
    await session.commit()
    return client, plaintext


async def _seed(session, client: Client):
    policy = CommercialControlPolicy(
        name="RBAC portal policy",
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
        target_id="rbac-invoice",
        summary="rbac summary",
        actor="rbac-user",
    )
    await require_approval_chain(
        session,
        client_id=client.id,
        policy=policy,
        target_type="invoice",
        target_id="rbac-invoice",
        requested_by="rbac-user",
        evidence_package_id=evidence.id,
    )
    await open_exception(
        session,
        client_id=client.id,
        control_policy_id=policy.id,
        exception_type="rbac_exception",
        severity="medium",
        description="rbac exception",
        owner="rbac-user",
    )
    await session.commit()


@pytest.mark.asyncio
async def test_readonly_cannot_export_but_can_view(portal_http_client, session):
    client, key = await _make_client_key(session, name="readonly", scopes=["enterprise_readonly"])
    await _seed(session, client)

    list_resp = await portal_http_client.get("/portal/audit/exceptions", headers={"Authorization": f"Bearer {key}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    export_resp = await portal_http_client.post(
        "/portal/audit/reports/generate",
        headers={"Authorization": f"Bearer {key}"},
        json={"report_type": "audit", "period_start": "2026-01-01", "period_end": "2026-12-31", "export_format": "json"},
    )
    assert export_resp.status_code == 403


@pytest.mark.asyncio
async def test_auditor_can_export_audit_and_finance_cannot_view_audit_items(portal_http_client, session):
    client_auditor, auditor_key = await _make_client_key(session, name="auditor", scopes=["enterprise_auditor"])
    await _seed(session, client_auditor)
    client_finance, finance_key = await _make_client_key(session, name="finance", scopes=["enterprise_finance"])
    await _seed(session, client_finance)

    auditor_export = await portal_http_client.post(
        "/portal/audit/reports/generate",
        headers={"Authorization": f"Bearer {auditor_key}"},
        json={"report_type": "audit", "period_start": "2026-01-01", "period_end": "2026-12-31", "export_format": "json"},
    )
    assert auditor_export.status_code == 201

    finance_view = await portal_http_client.get(
        "/portal/audit/approval-chains",
        headers={"Authorization": f"Bearer {finance_key}"},
    )
    assert finance_view.status_code == 403


@pytest.mark.asyncio
async def test_finance_can_export_financial_summary(portal_http_client, session):
    client, key = await _make_client_key(session, name="finance-summary", scopes=["enterprise_finance"])
    await _seed(session, client)

    resp = await portal_http_client.post(
        "/portal/audit/reports/generate",
        headers={"Authorization": f"Bearer {key}"},
        json={"report_type": "financial_summary", "period_start": "2026-01-01", "period_end": "2026-12-31", "export_format": "json"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_admin_has_full_tenant_access(portal_http_client, session):
    client, key = await _make_client_key(session, name="admin-tenant", scopes=["enterprise_admin"])
    await _seed(session, client)

    for path in [
        "/portal/audit/approval-chains",
        "/portal/audit/evidence-packages",
        "/portal/audit/attestations",
        "/portal/audit/exceptions",
        "/portal/audit/access-logs",
    ]:
        resp = await portal_http_client.get(path, headers={"Authorization": f"Bearer {key}"})
        assert resp.status_code == 200
