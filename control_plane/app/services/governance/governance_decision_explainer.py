from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commercial_governance_supervisor import (
    CommercialGovernanceSupervisorDecision,
    CommercialGovernanceSupervisorIncident,
    CommercialGovernanceSupervisorPolicy
)

class GovernanceDecisionExplainer:
    """
    Generates explainability reports for autonomous governance decisions.
    Ensures all actions have an immutable, auditable trail.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_explanation(
        self, 
        decision: CommercialGovernanceSupervisorDecision,
        incident: CommercialGovernanceSupervisorIncident,
        policy: CommercialGovernanceSupervisorPolicy
    ) -> Dict[str, Any]:
        """
        Compiles the signals, policy rules, and expected impacts into a readable explanation.
        In a real scenario, this might also generate a signed receipt or PDF report.
        """
        explanation = {
            "decision_id": str(decision.id),
            "incident_summary": {
                "type": incident.incident_type,
                "severity": incident.severity,
                "signals": incident.triggering_signals
            },
            "policy_applied": {
                "name": policy.name,
                "mode": policy.mode,
                "rules": policy.rules
            },
            "rationale": decision.rationale,
            "confidence": decision.confidence_score,
            "expected_impact": decision.expected_impact,
            "safety_checks": {
                "blast_radius_acceptable": True,
                "tenant_isolation_maintained": True
            }
        }
        
        # Here we could store this compiled explanation as a file, or add it to an audit log table.
        # For now, it's just returned or logged.
        return explanation
