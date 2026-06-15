from typing import Any


class RemediationApprovalRequirementService:
    """
    Determines approval requirements for a remediation plan.
    Strictly declarative, does not initiate workflows.
    """

    def determine_required_approvals(
        self, plan: dict[str, Any], steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Identifies which approvals are needed based on plan and steps.
        """
        requirements = []

        # Rule: Critical risk always requires executive approval
        if plan.get("risk_level") == "critical":
            requirements.append(
                {
                    "approval_scope": "executive",
                    "required_role": "operations_director",
                    "reason": "Plan involves critical risk level.",
                }
            )

        # Rule: High blast radius requires cross-domain approval
        if plan.get("blast_radius") in ["high", "critical"]:
            requirements.append(
                {
                    "approval_scope": "cross_domain",
                    "required_role": "system_architect",
                    "reason": "Plan has a high/critical blast radius affecting multiple domains.",
                }
            )

        # Rule: Irreversible steps require explicit approval
        irreversible_steps = [s for s in steps if not s.get("reversible", True)]
        if irreversible_steps:
            requirements.append(
                {
                    "approval_scope": "technical_risk",
                    "required_role": "senior_engineer",
                    "reason": f"Plan contains {len(irreversible_steps)} irreversible steps.",
                }
            )

        return requirements

    def build_approval_requirements(
        self, plan: dict[str, Any], steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Wrapper to build the full approval requirements list.
        """
        return self.determine_required_approvals(plan, steps)
