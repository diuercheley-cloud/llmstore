from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.services.operations.plugin_runtime.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload

signature_placeholder = "conceptual_only_no_real_crypto"


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


def build_abi_contract_receipt(contract: Any) -> dict[str, Any]:
    return _build_receipt("abi_contract_receipt", str(contract.client_id), str(contract.id), contract.immutable_hash, contract.contract_hash, contract.deterministic_version)


def build_load_plan_receipt(load_plan: Any) -> dict[str, Any]:
    return _build_receipt("load_plan_receipt", str(load_plan.client_id), str(load_plan.id), load_plan.immutable_hash, load_plan.load_plan_hash, "v1")


def build_compatibility_receipt(result: Any) -> dict[str, Any]:
    payload_hash = sha256_hex({"compatibility_status": result.compatibility_status, "runtime_version": result.runtime_version, "reason": result.reason})
    return _build_receipt("compatibility_receipt", str(result.client_id), str(result.id), result.immutable_hash, payload_hash, "v1")


def build_replay_verification_receipt(result: Any) -> dict[str, Any]:
    return _build_receipt("replay_verification_receipt", str(result.client_id), str(result.id), result.immutable_hash, result.replay_hash, "v1")


def build_federation_compatibility_receipt(result: Any) -> dict[str, Any]:
    return _build_receipt("federation_compatibility_receipt", str(result.client_id), str(result.id), result.immutable_hash, result.compatibility_hash, "v1")
