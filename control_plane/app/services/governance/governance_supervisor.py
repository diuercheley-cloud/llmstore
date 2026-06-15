import uuid
from typing import Any

from app.models.commercial.commercial_governance_supervisor import (
    CommercialGovernanceSupervisorDecision,
    CommercialGovernanceSupervisorIncident,
    CommercialGovernanceSupervisorPolicy,
)
from app.services.governance.governance_autoremediation import GovernanceAutoRemediation
from app.services.governance.governance_decision_explainer import GovernanceDecisionExplainer
from app.services.governance.governance_risk_engine import GovernanceRiskEngine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class GovernanceSupervisor:
    """
    Autonomous Governance Supervisor AI (Policy-Aware).
    Detects drift, assesses risk, and triggers policy-aware auto-remediation
    in advisory, dry_run, guarded_enforce, or sovereign_restricted modes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_engine = GovernanceRiskEngine(db)
        self.remediation = GovernanceAutoRemediation(db)
        self.explainer = GovernanceDecisionExplainer(db)

    async def analyze_system_state(
        self, client_id: uuid.UUID | None = None
    ) -> list[CommercialGovernanceSupervisorIncident]:
        """
        Gathers anomalies, drift signals, and risk factors to generate incidents.
        """
        # Calculate risk scores
        risk_score = await self.risk_engine.calculate_risk(client_id)

        incidents = []
        if risk_score.overall_risk_score > 0.7:
            incident = CommercialGovernanceSupervisorIncident(
                incident_type="high_overall_risk",
                severity="high" if risk_score.overall_risk_score < 0.9 else "critical",
                client_id=client_id,
                title="System-wide high risk detected",
                description=f"Overall risk score reached {risk_score.overall_risk_score}",
                triggering_signals={"overall_risk_score": risk_score.overall_risk_score},
                status="open",
            )
            self.db.add(incident)
            incidents.append(incident)

        if risk_score.financial_risk > 0.8:
            incident = CommercialGovernanceSupervisorIncident(
                incident_type="financial_risk_breach",
                severity="critical",
                client_id=client_id,
                title="Financial Risk Threshold Breached",
                description="Financial risk score indicates potential revenue loss or budget overrun.",
                triggering_signals={"financial_risk": risk_score.financial_risk},
                status="open",
            )
            self.db.add(incident)
            incidents.append(incident)

        if risk_score.compliance_risk > 0.75:
            incident = CommercialGovernanceSupervisorIncident(
                incident_type="compliance_drift",
                severity="high",
                client_id=client_id,
                title="Compliance Drift Detected",
                description="System runtime drifting from compliance policies.",
                triggering_signals={"compliance_risk": risk_score.compliance_risk},
                status="open",
            )
            self.db.add(incident)
            incidents.append(incident)

        await self.db.commit()
        return incidents

    async def process_incident(
        self, incident: CommercialGovernanceSupervisorIncident
    ) -> CommercialGovernanceSupervisorDecision | None:
        """
        Evaluate an incident and create a remediation decision based on active policies.
        """
        # Fetch relevant policies
        query = select(CommercialGovernanceSupervisorPolicy).where(
            CommercialGovernanceSupervisorPolicy.is_active == True
        )
        result = await self.db.execute(query)
        policies = result.scalars().all()

        # Simple policy matching logic for the sake of the supervisor
        matched_policy = None
        for policy in policies:
            if policy.policy_type in incident.incident_type or (
                policy.policy_type == "financial" and "financial" in incident.incident_type
            ):
                matched_policy = policy
                break

        if not matched_policy:
            # Fallback to a default advisory policy if no match
            matched_policy = CommercialGovernanceSupervisorPolicy(
                name=f"default_fallback_{uuid.uuid4()}", policy_type="fallback", mode="advisory"
            )

        # Generate decision
        decision = CommercialGovernanceSupervisorDecision(
            incident_id=incident.id,
            policy_id=matched_policy.id if matched_policy.id else None,
            decision_type="auto_remediation_proposal",
            confidence_score=0.85,
            rationale=f"Triggered by incident {incident.title} matching policy {matched_policy.name}",
            expected_impact={"risk_reduction": 0.3},
            mode_used=matched_policy.mode,
            is_approved=not matched_policy.approval_required,
        )
        self.db.add(decision)
        await self.db.commit()
        await self.db.refresh(decision)

        # Generate explainability report
        await self.explainer.generate_explanation(decision, incident, matched_policy)

        # Trigger remediation actions based on decision mode
        if decision.is_approved or decision.mode_used in ["advisory", "dry_run"]:
            await self.remediation.execute_decision(decision)

        return decision

    async def run_supervisor_cycle(self) -> dict[str, Any]:
        """
        Main entrypoint for background task or cron.
        """
        incidents = await self.analyze_system_state()
        decisions = []
        for incident in incidents:
            decision = await self.process_incident(incident)
            if decision:
                decisions.append(decision)

        return {
            "incidents_created": len(incidents),
            "decisions_made": len(decisions),
            "status": "completed",
        }
