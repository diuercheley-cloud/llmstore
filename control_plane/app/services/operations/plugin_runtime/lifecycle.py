from typing import Any

from app.models.operations.plugin_runtime import PluginLifecycleEvent
from app.services.operations.plugin_runtime.hash_utils import sha256_hex


class PluginLifecycleService:
    def _event(self, contract: Any, event_type: str, lifecycle_status: str, reason: str = "") -> PluginLifecycleEvent:
        if event_type in {"revoked", "blocked"} and not reason.strip():
            raise ValueError("reason is required")
        logical_payload = {
            "client_id": str(contract.client_id),
            "abi_contract_id": contract.id,
            "lifecycle_event_type": event_type,
            "lifecycle_status": lifecycle_status,
            "reason": reason.strip(),
        }
        return PluginLifecycleEvent(
            id=sha256_hex({"kind": "plugin_lifecycle_event_id", **logical_payload}),
            client_id=contract.client_id,
            abi_contract_id=contract.id,
            lifecycle_event_type=event_type,
            lifecycle_status=lifecycle_status,
            reason=reason.strip(),
            immutable_hash=sha256_hex({"kind": "plugin_lifecycle_event", **logical_payload}),
        )

    def submit_plugin(self, contract: Any) -> PluginLifecycleEvent:
        return self._event(contract, "submitted", "accepted")

    def mark_reviewed(self, contract: Any) -> PluginLifecycleEvent:
        return self._event(contract, "reviewed", "accepted")

    def mark_compatibility_checked(self, contract: Any) -> PluginLifecycleEvent:
        return self._event(contract, "compatibility_checked", "accepted")

    def mark_sandbox_validated(self, contract: Any) -> PluginLifecycleEvent:
        return self._event(contract, "sandbox_validated", "accepted")

    def mark_placeholder_certified(self, contract: Any) -> PluginLifecycleEvent:
        return self._event(contract, "placeholder_certified", "warning", "placeholder certification only")

    def deprecate_plugin(self, contract: Any, reason: str) -> PluginLifecycleEvent:
        contract.contract_status = "deprecated"
        return self._event(contract, "deprecated", "warning", reason)

    def revoke_plugin(self, contract: Any, reason: str) -> PluginLifecycleEvent:
        contract.contract_status = "revoked"
        return self._event(contract, "revoked", "denied", reason)

    def block_plugin(self, contract: Any, reason: str) -> PluginLifecycleEvent:
        contract.contract_status = "blocked"
        return self._event(contract, "blocked", "denied", reason)
