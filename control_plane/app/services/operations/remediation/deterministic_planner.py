import hashlib
import json
from typing import Any


class DeterministicRemediationPlanner:
    """
    Generates deterministic remediation plans based on failure forecasts, risk assessments, or correlations.
    Strictly advisory-only. No real actions are executed.
    """

    def __init__(self, version: str = "v1"):
        self.version = version

    def normalize_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Ensures inputs are in a consistent format for hashing."""
        # Simple normalization: sort keys and handle basic types
        return {k: inputs[k] for k in sorted(inputs.keys())}

    def compute_input_hash(self, inputs: dict[str, Any]) -> str:
        """Computes a deterministic hash of the inputs."""
        normalized = self.normalize_inputs(inputs)
        raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(f"{self.version}:{raw}".encode()).hexdigest()

    def build_plan(self, inputs: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
        """
        Builds a remediation plan based on heuristics.
        Logic is deterministic: same input -> same plan.
        """
        source_type = inputs.get("source_type", "unknown")
        source_ref = inputs.get("source_ref", "unknown")
        risk_level = inputs.get("risk_level", "low")

        # Determine plan type based on source and risk
        plan_type = f"remediation_{source_type}_{risk_level}"

        # Basic blast radius logic
        involved_domains = inputs.get("involved_domains", [])
        if len(involved_domains) > 3 or risk_level == "critical":
            blast_radius = "high"
        elif len(involved_domains) > 1:
            blast_radius = "medium"
        else:
            blast_radius = "low"

        requires_approval = risk_level in ["high", "critical"] or blast_radius == "high"

        plan_data = {
            "plan_type": plan_type,
            "source_type": source_type,
            "source_ref": source_ref,
            "risk_level": risk_level,
            "blast_radius": blast_radius,
            "requires_approval": requires_approval,
            "advisory_only": True,
            "dry_run": dry_run,
            "deterministic_version": self.version,
            "status": "proposed",
        }

        return plan_data

    def build_steps(self, plan: dict[str, Any], inputs: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generates remediation steps deterministically.
        """
        steps = []
        involved_domains = inputs.get("involved_domains", ["system"])

        # Heuristic: Containment -> Mitigation -> Recovery -> Validation

        # 1. Containment
        for i, domain in enumerate(involved_domains):
            steps.append(
                {
                    "step_order": i + 1,
                    "action_type": "containment",
                    "target_domain": domain,
                    "target_ref": f"{domain}_circuit_breaker",
                    "description": f"Isolate {domain} to prevent failure propagation.",
                    "expected_effect": f"Failure isolated within {domain}.",
                    "reversible": True,
                    "requires_approval": plan["risk_level"] == "critical",
                    "advisory_only": True,
                    "dry_run": plan["dry_run"],
                }
            )

        # 2. Mitigation/Recovery
        base_order = len(steps)
        for i, domain in enumerate(involved_domains):
            steps.append(
                {
                    "step_order": base_order + i + 1,
                    "action_type": "mitigation",
                    "target_domain": domain,
                    "target_ref": f"{domain}_resource_reallocation",
                    "description": f"Reallocate resources for {domain} to restore stability.",
                    "expected_effect": f"{domain} performance normalized.",
                    "reversible": True,
                    "requires_approval": plan["requires_approval"],
                    "advisory_only": True,
                    "dry_run": plan["dry_run"],
                }
            )

        # 3. Validation
        steps.append(
            {
                "step_order": len(steps) + 1,
                "action_type": "validation",
                "target_domain": "global",
                "target_ref": "health_check_suite",
                "description": "Verify system health after remediation steps.",
                "expected_effect": "All health checks passing.",
                "reversible": True,
                "requires_approval": False,
                "advisory_only": True,
                "dry_run": plan["dry_run"],
            }
        )

        return steps

    def explain_plan(self, plan: dict[str, Any], steps: list[dict[str, Any]]) -> str:
        """Generates a human-readable explanation of the plan."""
        explanation = [
            f"Remediation Plan: {plan['plan_type']}",
            f"Risk Level: {plan['risk_level'].upper()}",
            f"Blast Radius: {plan['blast_radius'].upper()}",
            f"Requires Approval: {plan['requires_approval']}",
            "",
            "Proposed Steps:",
        ]
        for step in steps:
            explanation.append(
                f"{step['step_order']}. [{step['action_type'].upper()}] {step['description']}"
            )

        explanation.append("")
        explanation.append(
            "Note: This plan is advisory-only and for dry-run purposes. No actual changes will be performed."
        )

        return "\n".join(explanation)
