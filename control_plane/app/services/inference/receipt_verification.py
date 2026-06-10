from __future__ import annotations

from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_cryptographic_receipts import (
    CommercialInferenceReceipt,
    CommercialInferenceReceiptVerificationReport,
)
from app.services.inference.cryptographic_receipts import (
    _canonical_json,
    _sha256,
    build_receipt_hash,
    summarize_receipt,
    verify_payload_signature,
)
from sqlalchemy.ext.asyncio import AsyncSession


def _verify_detached_signature(receipt_hash: str, signature: str | None, algorithm: str | None) -> bool:
    if not signature:
        return False
    return verify_payload_signature(receipt_hash, signature)


def verify_receipt_signature(receipt: CommercialInferenceReceipt) -> bool:
    return _verify_detached_signature(
        receipt.receipt_hash,
        receipt.detached_signature,
        receipt.signature_algorithm,
    )


def verify_receipt_hash(receipt: CommercialInferenceReceipt, metadata: dict[str, Any] | None = None) -> bool:
    recomputed = build_receipt_hash(
        prompt_hash=receipt.prompt_hash,
        response_hash=receipt.response_hash,
        previous_receipt_hash=receipt.previous_receipt_hash,
        request_payload_hash=receipt.request_payload_hash,
        response_payload_hash=receipt.response_payload_hash,
        runtime_snapshot_hash=receipt.runtime_snapshot_hash,
        routing_decision_hash=receipt.routing_decision_hash,
        client_id=receipt.client_id,
        model_name=receipt.model_name,
        metadata_json=metadata or receipt.metadata_json,
    )
    return recomputed == receipt.receipt_hash


def verify_receipt_timestamp(receipt: CommercialInferenceReceipt) -> bool:
    if not receipt.timestamp_token:
        return False
    return bool(len(receipt.timestamp_token) > 20)


def verify_receipt_chain(
    chain: list[dict[str, Any]],
) -> dict[str, Any]:
    chain_valid = True
    broken_links: list[int] = []
    for i in range(len(chain) - 1):
        current = chain[i]
        previous = chain[i + 1]
        if current.get("previous_receipt_hash") and current["previous_receipt_hash"] != previous.get("receipt_hash"):
            chain_valid = False
            broken_links.append(i)
    return {
        "chain_valid": chain_valid,
        "chain_length": len(chain),
        "broken_links": broken_links,
    }


async def detect_receipt_tampering(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
) -> dict[str, Any]:
    tamper_reasons: list[str] = []

    hash_ok = verify_receipt_hash(receipt)
    if not hash_ok:
        tamper_reasons.append("hash_mismatch")

    sig_ok = verify_receipt_signature(receipt)
    if not sig_ok:
        tamper_reasons.append("signature_invalid")

    ts_ok = verify_receipt_timestamp(receipt)
    if not ts_ok:
        tamper_reasons.append("timestamp_invalid")

    if tamper_reasons:
        receipt.verification_status = "tampered"
        receipt.tamper_reason = ";".join(tamper_reasons)
        receipt.verified_at = utc_now()
        await session.flush()

    report_payload = {
        "receipt_id": str(receipt.id),
        "hash_valid": hash_ok,
        "signature_valid": sig_ok,
        "timestamp_valid": ts_ok,
        "tamper_reasons": tamper_reasons,
        "verification_status": receipt.verification_status,
    }
    return report_payload


async def generate_verification_report(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
    *,
    replay_record=None,
    runtime_snapshot=None,
) -> dict[str, Any]:
    hash_ok = verify_receipt_hash(receipt)
    sig_ok = verify_receipt_signature(receipt)
    ts_ok = verify_receipt_timestamp(receipt)

    replay_match = None
    runtime_match = None
    drift_detected = None

    if replay_record is not None and hasattr(replay_record, "replay_similarity"):
        replay_match = replay_record.replay_similarity and replay_record.replay_similarity >= 0.85
        drift_detected = replay_record.replay_status == "drift_detected" if not drift_detected else drift_detected

    if runtime_snapshot is not None and receipt.runtime_snapshot_hash:
        if isinstance(runtime_snapshot, dict):
            snap_hash = runtime_snapshot.get("snapshot_hash", "")
        else:
            snap_hash = getattr(runtime_snapshot, "snapshot_hash", "")
        runtime_match = snap_hash == receipt.runtime_snapshot_hash

    if hash_ok and sig_ok:
        result = "valid"
    elif not hash_ok:
        result = "invalid"
    else:
        result = "partial"

    report_payload = {
        "receipt_id": str(receipt.id),
        "verification_result": result,
        "chain_valid": verify_receipt_chain([summarize_receipt(receipt)])["chain_valid"],
        "signature_valid": sig_ok,
        "timestamp_valid": ts_ok,
        "runtime_match": runtime_match,
        "replay_match": replay_match,
        "drift_detected": drift_detected,
        "hash_valid": hash_ok,
    }
    report_hash = _sha256(_canonical_json(report_payload))
    report_payload["report_hash"] = report_hash

    report = CommercialInferenceReceiptVerificationReport(
        receipt_id=receipt.id,
        verification_result=result,
        chain_valid=report_payload["chain_valid"],
        signature_valid=sig_ok,
        timestamp_valid=ts_ok,
        runtime_match=runtime_match,
        replay_match=replay_match,
        drift_detected=drift_detected,
        report_hash=report_hash,
    )
    session.add(report)
    await session.flush()

    return report_payload
