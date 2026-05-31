from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.services.operations.federation_sync.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload


def _build_receipt(receipt_type: str, client_id: str, subject_id: str, immutable_hash: str, payload_hash: str, deterministic_version: str) -> dict[str, Any]:
    generated_at = utc_now()
    return {
        "receipt_type": receipt_type,
        "client_id": client_id,
        "subject_id": subject_id,
        "immutable_hash": immutable_hash,
        "payload_hash": payload_hash,
        "deterministic_version": deterministic_version,
        "signature": sign_payload(f"{receipt_type}:{payload_hash[:16]}"),
        "generated_at": generated_at if isinstance(generated_at, datetime) else utc_now(),
    }


def build_sync_session_receipt(session: Any) -> dict[str, Any]:
    return _build_receipt(
        "sync_session_receipt",
        str(session.client_id),
        str(session.id),
        session.immutable_hash,
        session.session_hash,
        session.deterministic_version,
    )


def build_bundle_receipt(bundle: Any) -> dict[str, Any]:
    return _build_receipt(
        "bundle_receipt",
        str(bundle.client_id),
        str(bundle.id),
        bundle.immutable_hash,
        bundle.bundle_hash,
        getattr(bundle, "deterministic_version", "v1"),
    )


def build_conflict_resolution_receipt(conflict: Any) -> dict[str, Any]:
    payload_hash = sha256_hex(
        {
            "conflict_type": conflict.conflict_type,
            "resolution_strategy": conflict.resolution_strategy,
            "resolution_status": conflict.resolution_status,
        }
    )
    return _build_receipt(
        "conflict_resolution_receipt",
        str(conflict.client_id),
        str(conflict.id),
        conflict.immutable_hash,
        payload_hash,
        "v1",
    )


def build_trust_negotiation_receipt(negotiation: Any) -> dict[str, Any]:
    payload_hash = sha256_hex(
        {
            "negotiation_status": negotiation.negotiation_status,
            "required_trust_level": negotiation.required_trust_level,
            "negotiated_trust_level": negotiation.negotiated_trust_level,
        }
    )
    return _build_receipt(
        "trust_negotiation_receipt",
        str(negotiation.client_id),
        str(negotiation.id),
        negotiation.immutable_hash,
        payload_hash,
        "v1",
    )
