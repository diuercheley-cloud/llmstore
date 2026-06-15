from typing import Any


class RemediationRollbackPlanningService:
    """
    Generates rollback plans for remediation executions.
    Advisory-only.
    """

    def build_rollback_plan(
        self, plan: dict[str, Any], steps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Creates a rollback plan by inverting reversible steps.
        """
        rollback_steps = []

        # Steps are rolled back in reverse order
        for step in reversed(steps):
            if step.get("reversible", True):
                rollback_steps.append(
                    {
                        "step_order": len(rollback_steps) + 1,
                        "action_type": f"rollback_{step['action_type']}",
                        "target_domain": step["target_domain"],
                        "target_ref": step["target_ref"],
                        "description": f"Rollback: {step['description']}",
                        "expected_effect": f"Revert state for {step['target_domain']}",
                        "reversible": True,
                    }
                )

        return {
            "rollback_strategy": "reverse_ordered_inversion",
            "rollback_steps_json": rollback_steps,
            "approval_required": plan.get("requires_approval", False),
            "advisory_only": True,
            "dry_run": True,
        }

    def validate_rollback_plan(self, rollback_plan: dict[str, Any]) -> bool:
        """
        Validates that a rollback plan is complete.
        """
        steps = rollback_plan.get("rollback_steps_json", [])
        return len(steps) > 0

    def explain_rollback_plan(self, rollback_plan: dict[str, Any]) -> str:
        """
        Human-readable explanation of the rollback strategy.
        """
        strategy = rollback_plan.get("rollback_strategy")
        steps = rollback_plan.get("rollback_steps_json", [])

        explanation = [f"Rollback Strategy: {strategy}", f"Rollback Steps ({len(steps)}):"]

        for step in steps:
            explanation.append(f"{step['step_order']}. {step['description']}")

        return "\n".join(explanation)
