from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.services.operations.compatibility_contracts.hash_utils import sha256_hex
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


def build_contract_receipt(contract: Any) -> dict[str, Any]:
    return _build_receipt(
        "contract_receipt",
        str(contract.client_id),
        str(contract.id),
        contract.immutable_hash,
        contract.contract_hash,
        getattr(contract, "deterministic_version", "v1"),
    )


def build_negotiation_receipt(session: Any) -> dict[str, Any]:
    payload_hash = sha256_hex(
        {
            "source_version": session.source_version,
            "target_version": session.target_version,
            "negotiated_version": session.negotiated_version,
            "negotiation_status": session.negotiation_status,
        }
    )
    return _build_receipt(
        "negotiation_receipt",
        str(session.client_id),
        str(session.id),
        session.immutable_hash,
        payload_hash,
        "v1",
    )


def build_verification_receipt(result: Any) -> dict[str, Any]:
    payload_hash = sha256_hex(
        {
            "verification_type": result.verification_type,
            "verification_status": result.verification_status,
            "compatibility_summary": result.compatibility_summary,
        }
    )
    return _build_receipt(
        "verification_receipt",
        str(result.client_id),
        str(result.id),
        result.immutable_hash,
        payload_hash,
        "v1",
    )


def build_deprecation_receipt(lifecycle: Any) -> dict[str, Any]:
    payload_hash = sha256_hex(
        {
            "contract_id": lifecycle.contract_id,
            "deprecation_status": lifecycle.deprecation_status,
            "migration_required": lifecycle.migration_required,
        }
    )
    return _build_receipt(
        "deprecation_receipt",
        str(lifecycle.client_id),
        str(lifecycle.id),
        lifecycle.immutable_hash,
        payload_hash,
        "v1",
    )
