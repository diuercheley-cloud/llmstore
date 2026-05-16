from typing import Any

from app.services.operations.plugin_supply_chain.hash_utils import sha256_hex


PLUGIN_SUPPLY_CHAIN_AUDIT_EVENTS = {
    "provenance_created",
    "provenance_verified",
    "sbom_generated",
    "dependency_verification_completed",
    "lineage_verified",
    "supply_chain_receipt_created",
}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "credential", "signature", "payload")):
            sanitized[key] = "redacted"
        else:
            sanitized[key] = value
    return sanitized


def build_plugin_supply_chain_audit_event(event_type: str, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in PLUGIN_SUPPLY_CHAIN_AUDIT_EVENTS:
        raise ValueError("unsupported audit event type")
    sanitized = _sanitize_payload(payload)
    return {
        "event_type": event_type,
        "client_id": client_id,
        "payload": sanitized,
        "payload_hash": sha256_hex(sanitized),
        "offline_compatible": True,
        "signature_placeholder": f"placeholder-signature:audit:{event_type}",
    }
