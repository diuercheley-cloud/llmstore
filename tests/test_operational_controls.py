from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.commercial_compliance import CommercialOperationalControl, CommercialOperationalEvidence
from app.services.compliance.operational_controls import (
    add_operational_evidence,
    create_control,
    detect_stale_evidence,
)


@pytest.mark.asyncio
async def test_create_control_and_immutable_evidence_hash(session):
    control = await create_control(
        session,
        control_code="OPS-001",
        name="Quarterly access review",
        category="security",
        owner_email="owner@example.com",
        review_frequency="quarterly",
        evidence_sla_days=90,
    )
    await session.commit()

    evidence = await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="report",
        title="Quarterly access report",
        summary="sanitized summary",
        evidence_json={"secret": "drop-me", "result": "ok"},
    )
    await session.commit()

    stored_control = (await session.execute(select(CommercialOperationalControl))).scalar_one()
    stored_evidence = (await session.execute(select(CommercialOperationalEvidence))).scalar_one()
    assert stored_control.control_code == "OPS-001"
    assert stored_evidence.immutable_hash
    assert len(stored_evidence.immutable_hash) == 64
    assert "secret" not in (stored_evidence.evidence_json or {})


@pytest.mark.asyncio
async def test_stale_and_expired_evidence_detection(session):
    control = await create_control(
        session,
        control_code="OPS-002",
        name="Incident escalation evidence",
        category="availability",
        review_frequency="quarterly",
        evidence_sla_days=10,
    )
    await session.flush()

    fresh = await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="report",
        title="Fresh",
    )
    fresh.collected_at = fresh.created_at - timedelta(days=3)
    stale = await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="report",
        title="Stale",
    )
    stale.collected_at = stale.created_at - timedelta(days=8)
    expired = await add_operational_evidence(
        session,
        control_id=control.id,
        evidence_type="report",
        title="Expired",
    )
    expired.collected_at = expired.created_at - timedelta(days=12)
    await session.commit()

    flagged = await detect_stale_evidence(session)
    await session.commit()

    statuses = {item.title: item.freshness_status for item in flagged}
    assert statuses["Stale"] == "stale"
    assert statuses["Expired"] == "expired"
    assert "Fresh" not in statuses


@pytest.mark.asyncio
async def test_operational_control_endpoints_require_admin_auth(admin_client, admin_token_headers):
    unauth = await admin_client.get("/admin/compliance/operational-controls")
    assert unauth.status_code == 401

    create_resp = await admin_client.post(
        "/admin/compliance/operational-controls",
        headers=admin_token_headers,
        json={
            "control_code": "OPS-003",
            "name": "Capacity review",
            "category": "operational",
            "review_frequency": "quarterly",
            "evidence_sla_days": 30,
            "owner_email": "ops@example.com",
        },
    )
    assert create_resp.status_code == 201

    listing = await admin_client.get("/admin/compliance/operational-controls", headers=admin_token_headers)
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["summary"]["controls"] >= 1
