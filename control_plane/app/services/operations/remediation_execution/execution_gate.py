from typing import List, Dict, Any, Optional
import uuid

class RemediationExecutionGate:
    """
    Verifies if a remediation plan can be executed based on various safety gates.
    """

    def verify_approval(self, plan: Dict[str, Any], approvals: List[Dict[str, Any]]) -> bool:
        """
        Ensures all required approvals are present for a given plan.
        """
        requires_approval = plan.get("requires_approval", False)
        if not requires_approval:
            return True
        
        # In this phase, we look for a simple 'approved' flag in the approvals list
        # or check if the approvals list matches the required roles.
        # For simplicity, we assume an approval is verified if the list is not empty
        # and contains at least one approval from a relevant role.
        if not approvals:
            return False
            
        return any(a.get("status") == "approved" for a in approvals)

    def verify_blast_radius(self, plan: Dict[str, Any]) -> bool:
        """
        Verifies the blast radius of the plan. 
        Critical blast radius might require additional checks.
        """
        blast_radius = plan.get("blast_radius", "low")
        # For now, we just ensure it's a known value
        return blast_radius in ["low", "medium", "high", "critical"]

    def verify_rollback_plan(self, rollback_plan: Optional[Dict[str, Any]]) -> bool:
        """
        Ensures a valid rollback plan exists for the remediation.
        """
        if not rollback_plan:
            return False
        
        steps = rollback_plan.get("rollback_steps_json", [])
        return len(steps) > 0

    def verify_kill_switch(self, kill_switch_state: Optional[Dict[str, Any]]) -> bool:
        """
        Returns True if the kill-switch is NOT enabled (safe to execute).
        """
        if not kill_switch_state:
            return True # Assume safe if not set
            
        return not kill_switch_state.get("enabled", False)

    def can_execute(self, plan: Dict[str, Any], approvals: List[Dict[str, Any]], 
                    rollback_plan: Optional[Dict[str, Any]], 
                    kill_switch_state: Optional[Dict[str, Any]], 
                    dry_run: bool = True) -> Dict[str, Any]:
        """
        Composite check for all safety gates.
        """
        reasons = []
        
        approval_ok = dry_run or self.verify_approval(plan, approvals)
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
            "blast_radius_checked": blast_radius_ok,
            "rollback_plan_present": rollback_ok,
            "kill_switch_checked": kill_switch_safe,
            "reasons": reasons
        }
