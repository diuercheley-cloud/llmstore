from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.api.commercial_compliance_admin import router as compliance_router
from app.core.config import get_settings
from app.models.commercial_compliance import (
    CommercialApprovalChain,
    CommercialControlException,
    CommercialControlPolicy,
)
from app.models.commercial_financial_anomaly import CommercialFinancialAnomaly
from app.models.commercial_revenue_protection_action import CommercialRevenueProtectionAction
from app.models.commercial_revenue_protection_policy import CommercialRevenueProtectionPolicy
from app.services.billing.revenue_protection import apply_action
from app.services.compliance.financial_controls import (
    build_audit_report,
    create_attestation,
    evaluate_control_policy,
)
from sqlalchemy import select


@pytest.fixture(autouse=True)
def compliance_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_CONTROLS_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_MODE", "report_only")
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_REQUIRE_EVIDENCE", "true")
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_DEFAULT_APPROVER_COUNT", "1")
    monkeypatch.setenv("COMMERCIAL_COMPLIANCE_SEGREGATION_REQUIRED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ENABLED", "true")
    monkeypatch.setenv("COMMERCIAL_REVENUE_PROTECTION_ALLOW_ENFORCE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_policy_evaluation_report_only_creates_chain_and_does_not_block(session):
    policy = CommercialControlPolicy(
        name="Manual credit review",
        control_area="billing",
        action_type="manual_credit",
        requires_approval=True,
        required_approver_count=2,
        segregation_required=True,
        evidence_required=True,
        review_frequency="quarterly",
    )
    session.add(policy)
    await session.commit()

    decision = await evaluate_control_policy(
        session,
        control_area="billing",
        action_type="manual_credit",
        target_type="Client",
        target_id="client-1",
        actor="requester",
        package_type="manual_credit",
        summary="Manual credit",
        before_state={"balance": "0"},
        after_state={"balance": "10"},
        payload={"amount_brl": "10.00"},
        related_ids={"client_id": "client-1"},
    )
    await session.commit()

    assert decision.requires_approval is True
    assert decision.should_block is False
    assert decision.approval_chain is not None
    assert decision.evidence_package is not None

    chains = (await session.execute(select(CommercialApprovalChain))).scalars().all()
    assert len(chains) == 1
    assert chains[0].required_approver_count == 2


@pytest.mark.asyncio
async def test_attestation_flow_failed_creates_exception(session):
    policy = CommercialControlPolicy(
        name="Quarterly wallet review",
        control_area="wallet",
        action_type="qos_manual_debit",
        requires_approval=False,
        review_frequency="quarterly",
    )
    session.add(policy)
    await session.commit()

    attestation = await create_attestation(
        session,
        control_policy_id=policy.id,
        attested_by="finance-admin",
        attestation_period_start=date(2026, 1, 1),
        attestation_period_end=date(2026, 3, 31),
        status="failed",
        notes="Missing evidence for one approval chain",
    )
    await session.commit()

    assert attestation.status == "failed"
    exceptions = (await session.execute(select(CommercialControlException))).scalars().all()
    assert len(exceptions) == 1
    assert exceptions[0].exception_type == "attestation_failure"


@pytest.mark.asyncio
async def test_audit_report_export_contains_summary(session):
    policy = CommercialControlPolicy(
        name="Infra segregation",
        control_area="infra_execution",
        action_type="real_execution",
        requires_approval=True,
        review_frequency="quarterly",
    )
    session.add(policy)
    await session.commit()

    report = await build_audit_report(session)
    assert report["summary"]["active_controls"] >= 1
    assert report["policies"][0]["name"] == "Infra segregation"


@pytest.mark.asyncio
async def test_revenue_protection_apply_in_report_only_with_compliance_evidence(session):
    rp_policy = CommercialRevenueProtectionPolicy(
        name="Restrict costly provider",
        enabled=True,
        trigger_type="cost_spike",
        severity_threshold="high",
        action_type="notify",
        scope_type="global",
        mode="report_only",
        cooldown_minutes=60,
    )
    session.add(rp_policy)
    await session.flush()
    anomaly = CommercialFinancialAnomaly(
        anomaly_type="cost_spike",
        severity="high",
        status="open",
        provider="openai",
        observed_value_brl=Decimal("10.000000"),
        expected_value_brl=Decimal("2.000000"),
        deviation_percent=400.0,
        explanation="Cost spike",
        metadata_json={},
    )
    session.add(anomaly)
    await session.flush()
    action = CommercialRevenueProtectionAction(
        policy_id=rp_policy.id,
        anomaly_id=anomaly.id,
        action_type="notify",
        mode="report_only",
        status="proposed",
        before_state_json={},
        after_state_json={"notify": True},
    )
    session.add(action)
    await session.commit()

    decision = await evaluate_control_policy(
        session,
        control_area="revenue_protection",
        action_type="enforce_action",
        target_type="CommercialRevenueProtectionAction",
        target_id=action.id,
        actor="ops-admin",
        package_type="revenue_protection",
        summary="Apply revenue protection",
        before_state={"status": "proposed"},
        after_state={"status": "applied"},
        payload={"action_id": str(action.id)},
    )
    applied = await apply_action(session, action)
    await session.commit()

    assert decision.should_block is False
    assert applied.status == "applied"


@pytest.mark.asyncio
async def test_compliance_endpoints_require_admin_auth(fastapi_app, async_client):
    fastapi_app.include_router(compliance_router)
    response = await async_client.get("/admin/compliance/controls")
    assert response.status_code == 401
