from typing import Any

from app.services.operations.reproducible_builds.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload

REPRODUCIBLE_BUILD_AUDIT_EVENTS = {
    "reproducible_build_manifest_created",
    "artifact_verified",
    "lineage_verified",
    "replay_verification_completed",
    "build_environment_validated",
    "reproducibility_verification_completed",
    "reproducible_build_receipt_created",
}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "credential", "payload")):
            sanitized[key] = "redacted"
        else:
            sanitized[key] = value
    return sanitized


def build_reproducible_build_audit_event(event_type: str, client_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type not in REPRODUCIBLE_BUILD_AUDIT_EVENTS:
        raise ValueError("unsupported audit event type")
    sanitized = _sanitize_payload(payload)
    return {
        "event_type": event_type,
        "client_id": client_id,
        "payload": sanitized,
        "payload_hash": sha256_hex({"event_type": event_type, "payload": sanitized}),
        "offline_compatible": True,
        "signature": sign_payload(f"audit:{event_type}"),
    }
