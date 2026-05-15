from __future__ import annotations

import pytest

from app.api.commercial_compliance_admin import router as compliance_router
from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.compliance.financial_controls import create_evidence_package


@pytest.fixture(autouse=True)
def compliance_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_CONTROLS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_MODE", "report_only")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_evidence_package_sanitization(session):
    evidence = await create_evidence_package(
        session,
        package_type="manual_credit",
        target_type="Client",
        target_id="client-1",
        summary="Evidence package",
        actor="auditor",
        before_state={"balance": "0", "api_key": "secret"},
        after_state={"balance": "10"},
        payload={"prompt": "should-hide", "smtp_password": "hide-me", "safe": "ok"},
        related_ids={"client_id": "client-1"},
    )
    await session.commit()

    assert evidence.evidence_json["payload"].get("safe") == "ok"
    assert "prompt" not in evidence.evidence_json["payload"]
    assert "smtp_password" not in evidence.evidence_json["payload"]
    assert "api_key" not in evidence.evidence_json["before_state"]
    assert len(evidence.immutable_hash) == 64


@pytest.mark.asyncio
async def test_evidence_packages_endpoint_requires_admin_auth(fastapi_app, async_client):
    fastapi_app.include_router(compliance_router)
    response = await async_client.get("/admin/compliance/evidence-packages")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_report_endpoint_exports_json(fastapi_app, async_client, session, admin_token_headers):
    fastapi_app.include_router(compliance_router)

    async def override_get_db_session():
        yield session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    response = await async_client.get("/admin/compliance/audit-report?format=json", headers=admin_token_headers)
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
