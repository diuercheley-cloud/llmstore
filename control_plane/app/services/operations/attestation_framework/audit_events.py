from typing import Any

from app.services.operations.attestation_framework.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload

EVENT_TYPES = {
    "attestation_issued",
    "attestation_verified",
    "attestation_revoked",
    "attestation_chain_created",
    "attestation_bundle_exported",
    "attestation_bundle_imported",
    "attestation_bundle_verified",
    "attestation_replay_verified",
    "attestation_receipt_created",
}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "credential", "key", "payload")):
            sanitized[key] = "redacted"
        else:
            sanitized[key] = value
    return sanitized


def build_attestation_audit_event(event_type: str, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
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
