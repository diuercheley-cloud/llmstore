from typing import Any

from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.models.operations.adapter_sandbox import AdapterManifest


class AdapterPromotionGateService:
    def evaluate_gates(
        self,
        registry_entry: SignedAdapterRegistryEntry,
        target_stage: str,
        manifest: AdapterManifest,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluates all mandatory gates for a promotion target."""
        results = []

        # 1. registry_entry_exists
        results.append(
            {
                "gate_name": "registry_entry_exists",
                "gate_status": "passed" if registry_entry else "failed",
                "reason": "Registry entry found" if registry_entry else "Registry entry missing",
                "required": True,
                "blocking": True,
            }
        )

        # 2. registry_entry_approved
        is_approved = registry_entry.registry_status == "approved"
        results.append(
            {
                "gate_name": "registry_entry_approved",
                "gate_status": "passed" if is_approved else "failed",
                "reason": "Entry is in approved status"
                if is_approved
                else f"Entry status is {registry_entry.registry_status}",
                "required": target_stage in ["staging_simulated", "production_eligible"],
                "blocking": target_stage in ["staging_simulated", "production_eligible"],
            }
        )

        # 3. not_revoked
        is_revoked = registry_entry.registry_status == "revoked"
        results.append(
            {
                "gate_name": "not_revoked",
                "gate_status": "failed" if is_revoked else "passed",
                "reason": "Entry is revoked" if is_revoked else "Entry not revoked",
                "required": True,
                "blocking": True,
            }
        )

        # 4. not_blocklisted
        is_blocked = registry_entry.registry_status == "blocked" or context.get(
            "is_blocklisted", False
        )
        results.append(
            {
                "gate_name": "not_blocklisted",
                "gate_status": "failed" if is_blocked else "passed",
                "reason": "Entry is blocklisted" if is_blocked else "Entry not blocklisted",
                "required": True,
                "blocking": True,
            }
        )

        # 5. sandbox_manifest_valid
        is_manifest_valid = manifest is not None
        results.append(
            {
                "gate_name": "sandbox_manifest_valid",
                "gate_status": "passed" if is_manifest_valid else "failed",
                "reason": "Sandbox manifest found"
                if is_manifest_valid
                else "Sandbox manifest missing",
                "required": True,
                "blocking": True,
            }
        )

        # 6. sandbox_simulation_passed
        sandbox_passed = context.get("sandbox_simulation_passed", False)
        results.append(
            {
                "gate_name": "sandbox_simulation_passed",
                "gate_status": "passed" if sandbox_passed else "failed",
                "reason": "Sandbox simulation passed"
                if sandbox_passed
                else "Sandbox simulation failed or missing",
                "required": True,
                "blocking": True,
            }
        )

        # 7. no_policy_violations
        no_violations = context.get("no_policy_violations", False)
        results.append(
            {
                "gate_name": "no_policy_violations",
                "gate_status": "passed" if no_violations else "failed",
                "reason": "No policy violations found"
                if no_violations
                else "Policy violations detected",
                "required": True,
                "blocking": True,
            }
        )

        # 8. staging_simulation_required
        staging_passed = context.get("staging_simulation_passed", False)
        results.append(
            {
                "gate_name": "staging_simulation_required",
                "gate_status": "passed"
                if staging_passed
                else ("skipped" if target_stage != "production_eligible" else "failed"),
                "reason": "Staging simulation passed"
                if staging_passed
                else "Staging simulation required for production eligibility",
                "required": target_stage == "production_eligible",
                "blocking": target_stage == "production_eligible",
            }
        )

        # 9. approval_required_for_production_eligible
        results.append(
            {
                "gate_name": "approval_required_for_production_eligible",
                "gate_status": "passed"
                if (
                    target_stage != "production_eligible"
                    or context.get("production_approval_granted", False)
                )
                else "failed",
                "reason": "Production approval granted"
                if context.get("production_approval_granted")
                else "Approval required for production eligibility",
                "required": target_stage == "production_eligible",
                "blocking": target_stage == "production_eligible",
            }
        )

        # 10. signature_present
        has_sig = bool(registry_entry.signature)
        results.append(
            {
                "gate_name": "signature_present",
                "gate_status": "passed" if has_sig else "failed",
                "reason": "Signature present" if has_sig else "Signature missing",
                "required": True,
                "blocking": True,
            }
        )

        return results

    def explain_gate_results(self, results: list[dict[str, Any]]) -> str:
        failed = [r["gate_name"] for r in results if r["gate_status"] == "failed" and r["blocking"]]
        if not failed:
            return "All mandatory gates passed."
        return f"Promotion blocked by gates: {', '.join(failed)}"
