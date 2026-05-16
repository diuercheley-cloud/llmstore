from typing import Any

from app.models.operations.plugin_runtime import PluginIsolationPolicy
from app.services.operations.plugin_runtime.hash_utils import sha256_hex


class PluginIsolationPolicyService:
    def create_default_policy(self, client_id: Any) -> PluginIsolationPolicy:
        logical_payload = {
            "client_id": str(client_id),
            "policy_name": "default-offline-first",
            "isolation_level": "strict",
            "deny_network": True,
            "deny_subprocess": True,
            "deny_dynamic_import": True,
            "deny_external_filesystem_write": True,
            "deny_plaintext_secret_access": True,
        }
        immutable_hash = sha256_hex({"kind": "plugin_isolation_policy", **logical_payload})
        return PluginIsolationPolicy(
            id=sha256_hex({"kind": "plugin_isolation_policy_id", **logical_payload}),
            client_id=client_id,
            policy_name=logical_payload["policy_name"],
            isolation_level=logical_payload["isolation_level"],
            deny_network=True,
            deny_subprocess=True,
            deny_dynamic_import=True,
            deny_external_filesystem_write=True,
            deny_plaintext_secret_access=True,
            immutable_hash=immutable_hash,
        )

    def validate_policy(self, policy: PluginIsolationPolicy) -> dict[str, Any]:
        valid = (
            policy.deny_network
            and policy.deny_subprocess
            and policy.deny_dynamic_import
            and policy.deny_external_filesystem_write
            and policy.deny_plaintext_secret_access
        )
        return {"valid": valid, "offline_first": True}

    def enforce_policy(self, contract: Any, boundary: Any) -> dict[str, Any]:
        denied = (
            boundary.offline_only
            and not boundary.network_allowed
            and not boundary.subprocess_allowed
            and not boundary.filesystem_write_allowed
            and not boundary.external_secret_access_allowed
        )
        return {
            "contract_id": contract.id,
            "policy_enforced": denied,
            "activation_allowed": denied and contract.contract_status not in {"blocked", "revoked"},
            "no_dynamic_import_external": True,
        }

    def explain_policy(self, policy: PluginIsolationPolicy) -> dict[str, Any]:
        return {
            "policy_name": policy.policy_name,
            "isolation_level": policy.isolation_level,
            "validation": self.validate_policy(policy),
            "notes": [
                "deny_network=True",
                "deny_subprocess=True",
                "deny_dynamic_import=True",
                "deny_external_filesystem_write=True",
                "deny_plaintext_secret_access=True",
            ],
        }
