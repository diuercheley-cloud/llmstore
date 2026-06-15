import pytest
from app.models.commercial.commercial_governance_supervisor import (
    CommercialGovernanceSupervisorIncident,
    CommercialGovernanceSupervisorPolicy,
)
from app.services.governance.governance_supervisor import GovernanceSupervisor
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_supervisor_cycle(session: AsyncSession):
    supervisor = GovernanceSupervisor(session)
    result = await supervisor.run_supervisor_cycle()
    assert "incidents_created" in result
    assert "decisions_made" in result
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_process_incident(session: AsyncSession):
    # Setup test policy
    policy = CommercialGovernanceSupervisorPolicy(
        name="test_financial_policy",
        policy_type="financial",
        mode="advisory",
        approval_required=False,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)

    incident = CommercialGovernanceSupervisorIncident(
        incident_type="financial_risk_breach",
        severity="critical",
        title="Test Incident",
        description="A test incident",
        triggering_signals={"financial_risk": 0.9},
        status="open",
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)

    supervisor = GovernanceSupervisor(session)
    decision = await supervisor.process_incident(incident)

    assert decision is not None
    assert decision.incident_id == incident.id
    assert decision.policy_id == policy.id
    assert decision.mode_used == "advisory"
    assert decision.is_approved is True
