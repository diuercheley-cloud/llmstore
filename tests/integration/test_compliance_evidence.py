import pytest
from app.schemas.compliance_evidence import ComplianceFramework, EvidenceType
from app.services.compliance.evidence.collector import ComplianceEvidenceService


@pytest.mark.asyncio
async def test_evidence_collection_mock(session):
    service = ComplianceEvidenceService(session)
    frameworks = [ComplianceFramework.SOC2, ComplianceFramework.GDPR]

    items = await service.collect_evidence(frameworks)

    assert len(items) > 0
    assert all(item.framework in frameworks for item in items)
    assert any(item.evidence_type == EvidenceType.ACCESS_LOG for item in items)


def test_evidence_hash_determinism(session):
    service = ComplianceEvidenceService(session)
    data = {"test": "data", "secret": "sk-example1234567890abcdef1234567890"}

    ev1 = service._create_evidence(
        ComplianceFramework.SOC2, "C1", EvidenceType.AUDIT_LOG, "source", data
    )
    ev2 = service._create_evidence(
        ComplianceFramework.SOC2, "C1", EvidenceType.AUDIT_LOG, "source", data
    )

    assert ev1.content_hash == ev2.content_hash
    assert ev1.data["secret"] == "[REDACTED_API_KEY]"


def test_evidence_redaction():
    service = ComplianceEvidenceService(None)
    raw_data = {
        "key": "sk-example1234567890abcdef1234567890",
        "token": "token:test-admin-token-mock-value-123",
        "nested": {"password": "test-password-mock-value"},
    }

    redacted = service._redact_sensitive_data(raw_data)

    assert redacted["key"] == "[REDACTED_API_KEY]"
    assert redacted["token"] == "[REDACTED_TOKEN]"
    assert redacted["nested"]["password"] == "[REDACTED_PASSWORD]"


@pytest.mark.asyncio
async def test_compliance_api_flow(admin_client, session):
    headers = {"X-Admin-Token": "test-admin-token"}

    # 1. Collect
    payload = {"frameworks": ["SOC2", "GDPR"]}
    resp = await admin_client.post(
        "/api/admin/compliance/evidence/collect", json=payload, headers=headers
    )
    assert resp.status_code == 200
    collected = resp.json()
    assert len(collected) > 0

    # 2. List
    resp_list = await admin_client.get("/api/admin/compliance/evidence", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= len(collected)

    # 3. Export Markdown
    resp_exp = await admin_client.get(
        "/api/admin/compliance/evidence/export?format=markdown", headers=headers
    )
    assert resp_exp.status_code == 200
    assert "# Compliance Evidence Support Report" in resp_exp.text
    assert "Framework: SOC2" in resp_exp.text
