from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class RemediationExecutionGate:
    """
    Verifies if a remediation plan can be executed based on various safety gates.
    """

    def verify_approval(
        self,
        plan: dict[str, Any],
        approvals_payload: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Ensures all required approvals are present for a given plan.
        """
        requires_approval = plan.get("requires_approval", False)
        if not requires_approval:
            return {"verified": True, "approved_by": None}

        has_approval = False
        if approvals_payload:
            has_approval = any(a.get("status") == "approved" for a in approvals_payload)

        if has_approval:
            return {"verified": True, "approved_by": "system"}
        return {"verified": False, "approved_by": None}

    def verify_blast_radius(self, plan: dict[str, Any]) -> bool:
        """
        Verifies the blast radius of the plan.
        Critical blast radius might require additional checks.
        """
        blast_radius = plan.get("blast_radius", "low")
        return blast_radius in ["low", "medium", "high", "critical"]

    def verify_rollback_plan(self, rollback_plan: dict[str, Any] | None) -> bool:
        """
        Ensures a valid rollback plan exists for the remediation.
        """
        if not rollback_plan:
            return False
        steps = rollback_plan.get("rollback_steps_json", [])
        return len(steps) > 0

    def verify_kill_switch(self, kill_switch_state: dict[str, Any] | None) -> bool:
        """
        Returns True if the kill-switch is NOT enabled (safe to execute).
        """
        if not kill_switch_state:
            return True
        return not kill_switch_state.get("enabled", False)

    def can_execute(
        self,
        db: AsyncSession | None,
        plan: dict[str, Any],
        approvals_payload: list[dict[str, Any]],
        rollback_plan: dict[str, Any] | None,
        kill_switch_state: dict[str, Any] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """
        Composite check for all safety gates.
        """
        reasons = []

        approval_res = (
            {"verified": True, "approved_by": "dry_run_system"}
            if dry_run
            else self.verify_approval(plan, approvals_payload)
        )
        approval_ok = approval_res["verified"]
        if not approval_ok:
            reasons.append("Missing required approvals for non-dry-run execution.")

        blast_radius_ok = self.verify_blast_radius(plan)
        if not blast_radius_ok:
            reasons.append("Invalid or unverified blast radius.")

        rollback_ok = dry_run or self.verify_rollback_plan(rollback_plan)
        if not rollback_ok:
            reasons.append("No valid rollback plan present for non-dry-run execution.")

        kill_switch_safe = self.verify_kill_switch(kill_switch_state)
        if not kill_switch_safe:
            reasons.append("Global kill-switch is ENABLED for this client.")

        can_exec = approval_ok and blast_radius_ok and (dry_run or rollback_ok) and kill_switch_safe

        return {
            "can_execute": can_exec,
            "approval_verified": approval_ok,
            "approved_by": approval_res["approved_by"],
            "blast_radius_checked": blast_radius_ok,
            "rollback_plan_present": rollback_ok,
            "kill_switch_checked": kill_switch_safe,
            "reasons": reasons,
        }
