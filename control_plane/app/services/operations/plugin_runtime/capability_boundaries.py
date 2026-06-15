from typing import Any

from app.models.operations.plugin_runtime import PluginCapabilityBoundary
from app.services.operations.plugin_runtime.hash_utils import sha256_hex

RESTRICTED_CAPABILITIES = {
    "shell",
    "subprocess",
    "network",
    "dynamic_import",
    "external_filesystem_write",
    "plaintext_secret_access",
    "kubernetes_apply",
    "nomad_run",
    "proxmox_mutate",
    "hardware_attestation_real",
}


class PluginCapabilityBoundaryService:
    def evaluate_capabilities(self, boundary: PluginCapabilityBoundary) -> dict[str, Any]:
        allowed = sorted(set(boundary.allowed_capabilities_json or []))
        denied = sorted(
            set(boundary.denied_capabilities_json or [])
            | self.deny_restricted_capabilities(allowed)
        )
        effective_allowed = [capability for capability in allowed if capability not in denied]
        return {
            "allowed_capabilities": effective_allowed,
            "denied_capabilities": denied,
            "denied_precedence": True,
            "offline_only": boundary.offline_only,
            "network_allowed": boundary.network_allowed,
            "subprocess_allowed": boundary.subprocess_allowed,
            "filesystem_write_allowed": boundary.filesystem_write_allowed,
        }

    def deny_restricted_capabilities(self, capabilities: list[str]) -> set[str]:
        return {capability for capability in capabilities if capability in RESTRICTED_CAPABILITIES}

    def validate_boundary(self, boundary: PluginCapabilityBoundary) -> dict[str, Any]:
        evaluation = self.evaluate_capabilities(boundary)
        valid = (
            boundary.isolation_required
            and boundary.offline_only
            and not boundary.network_allowed
            and not boundary.subprocess_allowed
            and not boundary.filesystem_write_allowed
        )
        return {
            "valid": valid,
            "evaluation": evaluation,
            "reasons": [
                reason
                for reason, enabled in (
                    ("network_allowed=False is required", boundary.network_allowed),
                    ("subprocess_allowed=False is required", boundary.subprocess_allowed),
                    (
                        "filesystem_write_allowed=False is required",
                        boundary.filesystem_write_allowed,
                    ),
                    ("offline_only=True is required", not boundary.offline_only),
                    ("isolation_required=True is required", not boundary.isolation_required),
                )
                if enabled
            ],
        }

    def explain_boundary(self, boundary: PluginCapabilityBoundary) -> dict[str, Any]:
        return {
            "abi_contract_id": boundary.abi_contract_id,
            "immutable_hash": boundary.immutable_hash,
            "validation": self.validate_boundary(boundary),
            "notes": [
                "denied capabilities always win",
                "network/subprocess/filesystem write are blocked in this phase",
                "no external secrets in plaintext",
            ],
        }

    def build_boundary(self, payload: dict[str, Any]) -> PluginCapabilityBoundary:
        logical_payload = {
            "client_id": str(payload["client_id"]),
            "abi_contract_id": payload["abi_contract_id"],
            "allowed_capabilities_json": sorted(set(payload.get("allowed_capabilities_json", []))),
            "denied_capabilities_json": sorted(set(payload.get("denied_capabilities_json", []))),
            "isolation_required": payload.get("isolation_required", True),
            "offline_only": payload.get("offline_only", True),
            "network_allowed": payload.get("network_allowed", False),
            "subprocess_allowed": payload.get("subprocess_allowed", False),
            "filesystem_write_allowed": payload.get("filesystem_write_allowed", False),
            "external_secret_access_allowed": payload.get("external_secret_access_allowed", False),
        }
        immutable_hash = sha256_hex({"kind": "plugin_capability_boundary", **logical_payload})
        return PluginCapabilityBoundary(
            id=sha256_hex({"kind": "plugin_capability_boundary_id", **logical_payload}),
            client_id=payload["client_id"],
            abi_contract_id=payload["abi_contract_id"],
            allowed_capabilities_json=logical_payload["allowed_capabilities_json"],
            denied_capabilities_json=logical_payload["denied_capabilities_json"],
            isolation_required=logical_payload["isolation_required"],
            offline_only=logical_payload["offline_only"],
            network_allowed=logical_payload["network_allowed"],
            subprocess_allowed=logical_payload["subprocess_allowed"],
            filesystem_write_allowed=logical_payload["filesystem_write_allowed"],
            external_secret_access_allowed=logical_payload["external_secret_access_allowed"],
            immutable_hash=immutable_hash,
        )
