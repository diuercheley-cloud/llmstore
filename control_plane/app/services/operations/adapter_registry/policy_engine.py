from typing import Tuple

from app.models.operations.adapter_registry import AdapterRegistryPolicy, SignedAdapterRegistryEntry
from app.models.operations.adapter_sandbox import AdapterManifest


class AdapterRegistryPolicyEngine:
    def evaluate_manifest(self, manifest: AdapterManifest, policy: AdapterRegistryPolicy) -> Tuple[bool, str]:
        """Evaluates a manifest against a policy."""
        # Hard constraints from Phase 74
        if not manifest.sandbox_required:
            return False, "sandbox_required=False is blocked by registry policy"
        
        if not manifest.dry_run_default:
            return False, "dry_run_default=False is blocked by registry policy"
        
        if manifest.network_access_allowed:
            return False, "network_access_allowed=True is blocked by registry policy"
        
        if manifest.subprocess_allowed:
            return False, "subprocess_allowed=True is blocked by registry policy"
        
        if manifest.external_system_access_allowed:
            return False, "external_system_access_allowed=True is blocked by registry policy"

        # Policy specific checks
        allowed_types = policy.allowed_adapter_types_json.get("allowed_types", [])
        if manifest.adapter_type not in allowed_types:
            return False, f"adapter_type '{manifest.adapter_type}' is not in the allowlist"

        # Check denied capabilities (simplified)
        denied_caps = policy.denied_capabilities_json.get("denied", [])
        for cap in manifest.capabilities_json.get("requested", []):
            if cap in denied_caps:
                return False, f"Capability '{cap}' is explicitly denied by registry policy"

        return True, "Manifest complies with registry policy"

    def evaluate_registry_entry(self, entry: SignedAdapterRegistryEntry, policy: AdapterRegistryPolicy) -> Tuple[bool, str]:
        """Evaluates a registry entry against a policy."""
        if policy.require_approval and entry.registry_status not in ["approved", "revoked", "blocked", "deprecated"]:
            if entry.registry_status == "submitted":
                return True, "Entry is submitted and awaiting approval"
            return False, "Entry requires explicit approval"
        
        return True, "Entry complies with registry policy"

    def explain_policy_decision(self, result: Tuple[bool, str]) -> str:
        """Returns a human-readable explanation of a policy decision."""
        status = "Accepted" if result[0] else "Denied"
        return f"Decision: {status}. Reason: {result[1]}"
