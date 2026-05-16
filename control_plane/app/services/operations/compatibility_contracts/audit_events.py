from typing import Any

from app.services.operations.compatibility_contracts.hash_utils import sha256_hex


COMPATIBILITY_AUDIT_EVENTS = {
    "compatibility_contract_created",
    "compatibility_matrix_created",
    "version_negotiation_started",
    "version_negotiation_completed",
    "capability_negotiation_completed",
    "compatibility_verification_completed",
    "deprecation_proposed",
    "deprecation_announced",
    "deprecation_enforced",
    "compatibility_receipt_created",
}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "credential", "payload", "schema")):
            sanitized[key] = "redacted"
        else:
            sanitized[key] = value
    return sanitized


def build_compatibility_audit_event(event_type: str, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in COMPATIBILITY_AUDIT_EVENTS:
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
