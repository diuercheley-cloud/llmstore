from typing import Any

from app.services.operations.plugin_runtime.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload

PLUGIN_RUNTIME_AUDIT_EVENTS = {
    "plugin_abi_contract_created",
    "plugin_capability_boundary_evaluated",
    "plugin_runtime_compatibility_checked",
    "plugin_load_plan_created",
    "plugin_load_simulated",
    "plugin_isolation_policy_enforced",
    "plugin_lifecycle_event_recorded",
    "plugin_replay_verified",
    "plugin_federation_compatibility_checked",
    "plugin_runtime_receipt_created",
}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(
            marker in lowered
            for marker in ("secret", "token", "password", "credential", "payload", "raw")
        ):
            sanitized[key] = "redacted"
        else:
            sanitized[key] = value
    return sanitized


def build_plugin_runtime_audit_event(
    event_type: str, client_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    if event_type not in PLUGIN_RUNTIME_AUDIT_EVENTS:
        raise ValueError("unsupported audit event type")
    sanitized = _sanitize_payload(payload)
    return {
        "event_type": event_type,
        "client_id": client_id,
        "payload": sanitized,
        "payload_hash": sha256_hex(sanitized),
        "offline_compatible": True,
        "signature": sign_payload(f"audit:{event_type}"),
    }
