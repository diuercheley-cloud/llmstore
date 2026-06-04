import pytest
from app.models.commercial_governance_supervisor import (
    CommercialGovernanceSupervisorDecision,
    CommercialGovernanceSupervisorIncident,
    CommercialGovernanceSupervisorPolicy,
)
from app.services.governance.governance_decision_explainer import GovernanceDecisionExplainer
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_generate_explanation(session: AsyncSession):
    policy = CommercialGovernanceSupervisorPolicy(name="test_policy", policy_type="drift")
    incident = CommercialGovernanceSupervisorIncident(
        incident_type="drift", 
        severity="medium",
        title="Drift Event",
        description="Testing drift",
        triggering_signals={"drift": True}
    )
    decision = CommercialGovernanceSupervisorDecision(
        decision_type="notify",
        rationale="Because of drift",
        mode_used="advisory"
    )
    
    session.add_all([policy, incident, decision])
    await session.commit()

    explainer = GovernanceDecisionExplainer(session)
    explanation = await explainer.generate_explanation(decision, incident, policy)
    
    assert str(decision.id) == explanation["decision_id"]
    assert "rationale" in explanation
    assert "safety_checks" in explanation
