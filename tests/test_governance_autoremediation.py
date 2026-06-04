import pytest
from app.models.commercial_governance_supervisor import CommercialGovernanceSupervisorDecision
from app.services.governance.governance_autoremediation import GovernanceAutoRemediation
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_execute_decision_dry_run(session: AsyncSession):
    decision = CommercialGovernanceSupervisorDecision(
        decision_type="throttle",
        confidence_score=0.9,
        rationale="test rationale",
        mode_used="dry_run",
        is_approved=True
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)

    remediation = GovernanceAutoRemediation(session)
    result = await remediation.execute_decision(decision)
    
    assert result["status"] == "dry_run_completed"

@pytest.mark.asyncio
async def test_execute_decision_guarded_enforce(session: AsyncSession):
    decision = CommercialGovernanceSupervisorDecision(
        decision_type="quarantine",
        confidence_score=0.9,
        rationale="financial risk",
        mode_used="guarded_enforce",
        is_approved=True
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)

    remediation = GovernanceAutoRemediation(session)
    result = await remediation.execute_decision(decision)
    
    assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_execute_decision_unapproved_enforce(session: AsyncSession):
    decision = CommercialGovernanceSupervisorDecision(
        decision_type="block_runtime",
        confidence_score=0.9,
        rationale="compliance risk",
        mode_used="guarded_enforce",
        is_approved=False
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)

    remediation = GovernanceAutoRemediation(session)
    result = await remediation.execute_decision(decision)
    
    assert result["status"] == "failed_approval_required"
