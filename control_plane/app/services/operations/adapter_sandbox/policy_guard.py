from typing import Any, Dict, List


class AdapterSandboxPolicyGuard:
    """
    Real-time policy enforcement for adapter sandbox activities.
    """

    def inspect_manifest(self, manifest: Any) -> List[Dict[str, Any]]:
        """
        Inspects a manifest for architectural violations.
        """
        violations = []
        m_dict = manifest if isinstance(manifest, dict) else manifest.__dict__

        if m_dict.get("network_access_allowed"):
            violations.append({
                "violation_type": "network_policy",
                "severity": "critical",
                "description": "Network access is strictly forbidden in Phase 73 sandbox.",
                "blocked": True
            })

        if m_dict.get("subprocess_allowed"):
            violations.append({
                "violation_type": "subprocess_policy",
                "severity": "critical",
                "description": "Subprocess execution is strictly forbidden in Phase 73 sandbox.",
                "blocked": True
            })

        return violations

    def inspect_execution_request(self, context: Any, action_type: str) -> List[Dict[str, Any]]:
        """
        Inspects an execution request against the sandbox context.
        """
        violations = []
        
        if context.approval_required and not context.approval_verified:
            violations.append({
                "violation_type": "approval_missing",
                "severity": "critical",
                "description": "Approval is required for this adapter but not verified.",
                "blocked": True
            })

        if context.gates_required and not context.gates_verified:
            violations.append({
                "violation_type": "gates_missing",
                "severity": "high",
                "description": "Architectural gates must be verified before execution.",
                "blocked": True
            })

        if not context.can_perform(action_type):
            violations.append({
                "violation_type": "capability_denied",
                "severity": "high",
                "description": f"Action '{action_type}' is not in the allowed capabilities for this adapter.",
                "blocked": True
            })
            
        # Hard block on some types even if manifest claims it
        if action_type in ["shell", "root_exec", "raw_socket"]:
            violations.append({
                "violation_type": "unsafe_action",
                "severity": "critical",
                "description": f"Action '{action_type}' is architecturally blocked for all adapters.",
                "blocked": True
            })

        return violations

    def block_if_violation(self, violations: List[Dict[str, Any]]) -> bool:
        """Returns True if any violation requires blocking."""
        return any(v.get("blocked", False) for v in violations)

    def explain_violations(self, violations: List[Dict[str, Any]]) -> str:
        """Human-readable explanation of violations."""
        if not violations:
            return "No policy violations detected."
        
        reasons = [f"- [{v['severity'].upper()}] {v['description']}" for v in violations]
        return "Policy Violations:\n" + "\n".join(reasons)
