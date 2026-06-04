from typing import Any

from app.services.operations.federation_sync.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload

FEDERATION_SYNC_AUDIT_EVENTS = {
    "federation_environment_registered",
    "federation_sync_session_created",
    "federation_bundle_exported",
    "federation_bundle_imported",
    "federation_bundle_verified",
    "federation_conflict_detected",
    "federation_conflict_resolved",
    "federation_trust_negotiated",
    "federation_replay_verified",
    "federation_receipt_created",
}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "credential", "payload", "bundle_data")):
            sanitized[key] = "redacted"
        else:
            sanitized[key] = value
    return sanitized


def build_federation_sync_audit_event(event_type: str, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in FEDERATION_SYNC_AUDIT_EVENTS:
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
