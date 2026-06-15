from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.models.operations.reproducible_builds import ReproducibleBuildReceipt
from app.services.operations.reproducible_builds.hash_utils import sha256_hex
from app.utils.crypto_signer import sign_payload

signature_placeholder = "conceptual_only_no_real_crypto"


def _build_receipt_payload(
    receipt_type: str,
    client_id: str,
    subject_id: str,
    immutable_hash: str,
    payload_hash: str,
    deterministic_version: str,
) -> dict[str, Any]:
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


def _build_model_receipt(
    receipt_type: str, manifest: Any, subject_id: str, payload_hash: str
) -> ReproducibleBuildReceipt:
    payload = _build_receipt_payload(
        receipt_type=receipt_type,
        client_id=str(manifest.client_id),
        subject_id=subject_id,
        immutable_hash=manifest.immutable_hash,
        payload_hash=payload_hash,
        deterministic_version=manifest.deterministic_version,
    )
    receipt = ReproducibleBuildReceipt(
        id=sha256_hex(
            {
                "kind": "reproducible_build_receipt_id",
                "receipt_type": receipt_type,
                "subject_id": subject_id,
                "payload_hash": payload_hash,
            }
        ),
        client_id=manifest.client_id,
        build_manifest_id=manifest.id,
        receipt_type=payload["receipt_type"],
        payload_hash=payload["payload_hash"],
        immutable_hash=sha256_hex(
            {
                "kind": "reproducible_build_receipt_immutable",
                "receipt_type": receipt_type,
                "subject_id": subject_id,
                "payload_hash": payload_hash,
            }
        ),
        signature=payload["signature"],
        generated_at=payload["generated_at"],
    )
    receipt._payload = payload
    return receipt


def build_manifest_receipt(manifest: Any) -> ReproducibleBuildReceipt:
    return _build_model_receipt(
        "build_manifest_receipt", manifest, manifest.id, manifest.build_manifest_hash
    )


def build_artifact_receipt(manifest: Any, artifact_record: Any) -> ReproducibleBuildReceipt:
    return _build_model_receipt(
        "artifact_verification_receipt", manifest, artifact_record.id, artifact_record.artifact_hash
    )


def build_lineage_receipt(manifest: Any, lineage: Any) -> ReproducibleBuildReceipt:
    return _build_model_receipt("lineage_receipt", manifest, lineage.id, lineage.lineage_hash)


def build_reproducibility_receipt(
    manifest: Any, verification_result: Any
) -> ReproducibleBuildReceipt:
    payload_hash = sha256_hex(
        {
            "kind": "reproducibility_result_payload",
            "verification_result_id": verification_result.id,
            "immutable_hash": verification_result.immutable_hash,
        }
    )
    return _build_model_receipt(
        "reproducibility_receipt", manifest, verification_result.id, payload_hash
    )
