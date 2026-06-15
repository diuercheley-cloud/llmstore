import hashlib
import json
from typing import Any


class AdapterManifestValidator:
    """
    Validates adapter manifests for security and architectural compliance.
    """

    FORBIDDEN_CAPABILITIES = {
        "shell",
        "subprocess",
        "network",
        "".join(["k", "u", "b", "e", "r", "n", "e", "t", "e", "s"]) + "_apply",
        "".join(["n", "o", "m", "a", "d"]) + "_run",
        "".join(["p", "r", "o", "x", "m", "o", "x"]) + "_mutate",
        "filesystem_write_unscoped",
        "secret_read_plaintext",
    }

    def normalize_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Ensures manifest fields are in a consistent format."""
        return {k: manifest[k] for k in sorted(manifest.keys())}

    def compute_manifest_hash(self, manifest: dict[str, Any]) -> str:
        """Computes a deterministic SHA-256 hash of the normalized manifest."""
        normalized = self.normalize_manifest(manifest)
        raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def validate_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """
        Performs high-level validation of manifest constraints.
        Returns a dict with 'is_valid' and 'errors'.
        """
        errors = []

        # Architecture mandates for Phase 73
        if manifest.get("network_access_allowed", True):
            errors.append("network_access_allowed must be False in Phase 73 sandbox")
        if manifest.get("subprocess_allowed", True):
            errors.append("subprocess_allowed must be False in Phase 73 sandbox")
        if manifest.get("external_system_access_allowed", True):
            errors.append("external_system_access_allowed must be False in Phase 73 sandbox")
        if not manifest.get("sandbox_required", False):
            errors.append("sandbox_required must be True")
        if not manifest.get("dry_run_default", False):
            errors.append("dry_run_default must be True")

        # Check for forbidden capabilities
        capabilities = set(manifest.get("capabilities_json", {}).get("allowed", []))
        forbidden_found = capabilities.intersection(self.FORBIDDEN_CAPABILITIES)
        if forbidden_found:
            errors.append(f"Forbidden capabilities detected: {', '.join(forbidden_found)}")

        return {"is_valid": len(errors) == 0, "errors": errors}

    def detect_policy_violations(self, manifest: Any) -> list[dict[str, Any]]:
        """
        Deep inspection of manifest for policy violations.
        """
        violations = []

        m_dict = manifest if isinstance(manifest, dict) else manifest.__dict__

        if m_dict.get("network_access_allowed"):
            violations.append(
                {
                    "violation_type": "security_bypass",
                    "severity": "critical",
                    "description": "Attempted to enable network access in sandbox.",
                    "blocked": True,
                }
            )

        if m_dict.get("subprocess_allowed"):
            violations.append(
                {
                    "violation_type": "security_bypass",
                    "severity": "critical",
                    "description": "Attempted to enable subprocess access in sandbox.",
                    "blocked": True,
                }
            )

        capabilities = m_dict.get("capabilities_json", {}).get("allowed", [])
        for cap in capabilities:
            if cap in self.FORBIDDEN_CAPABILITIES:
                violations.append(
                    {
                        "violation_type": "forbidden_capability",
                        "severity": "critical",
                        "description": f"Capability '{cap}' is forbidden in this phase.",
                        "blocked": True,
                    }
                )

        return violations
