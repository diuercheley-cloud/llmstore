from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.services.operations.attestation_framework.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload


def _receipt_payload(receipt_type: str, client_id: str, subject_id: str, payload_hash: str, deterministic_version: str) -> dict[str, Any]:
    generated_at = utc_now()
    immutable_hash = sha256_hex(
        {
            "receipt_type": receipt_type,
            "client_id": client_id,
            "subject_id": subject_id,
            "payload_hash": payload_hash,
            "deterministic_version": deterministic_version,
        }
    )
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


def build_attestation_receipt(attestation: Any) -> dict[str, Any]:
    return _receipt_payload(
        "attestation_receipt",
        str(attestation.client_id),
        str(attestation.id),
        attestation.payload_hash,
        getattr(attestation, "deterministic_version", "v1"),
    )


def build_bundle_receipt(bundle: Any) -> dict[str, Any]:
    return _receipt_payload(
        "bundle_receipt",
        str(bundle.client_id),
        str(bundle.id),
        bundle.bundle_hash,
        "v1",
    )


def build_verification_receipt(result: Any) -> dict[str, Any]:
    return _receipt_payload(
        "verification_receipt",
        str(result.client_id),
        str(result.attestation_id),
        result.immutable_hash,
        "v1",
    )


def build_chain_receipt(chain: list[Any]) -> dict[str, Any]:
    subject_id = chain[0].attestation_id if chain else "empty-chain"
    client_id = str(chain[0].client_id) if chain else "unknown"
    payload_hash = sha256_hex([item.current_link_hash for item in chain])
    return _receipt_payload("chain_receipt", client_id, str(subject_id), payload_hash, "v1")
