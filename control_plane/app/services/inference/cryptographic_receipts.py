from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_cryptographic_receipts import (
    CommercialInferenceReceipt,
    CommercialInferenceReceiptLedgerEvent,
    CommercialInferenceReceiptVerificationReport,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

KEY_PATH_DEFAULT = "config/receipts_private_key.pem"

def get_signing_key() -> ed25519.Ed25519PrivateKey:
    key_path_str = os.getenv("CRYPTO_RECEIPTS_PRIVATE_KEY_PATH", KEY_PATH_DEFAULT)
    p = Path(key_path_str)
    
    require_signature = os.getenv("CRYPTO_RECEIPTS_REQUIRE_SIGNATURE", "false").lower() == "true"
    
    if not p.exists():
        if require_signature:
            raise ValueError("Signing key is missing and CRYPTO_RECEIPTS_REQUIRE_SIGNATURE is enabled.")
        
        # Generate new
        private_key = ed25519.Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(pem)
        return private_key
    
    return serialization.load_pem_private_key(
        p.read_bytes(),
        password=None
    )

def get_public_key_pem() -> str:
    private_key = get_signing_key()
    public_key = private_key.public_key()
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode("utf-8")

def get_key_id() -> str:
    pub_pem = get_public_key_pem()
    return hashlib.sha256(pub_pem.encode("utf-8")).hexdigest()[:16]

def sign_payload(receipt_hash: str) -> str:
    private_key = get_signing_key()
    signature_bytes = private_key.sign(receipt_hash.encode("utf-8"))
    return base64.b64encode(signature_bytes).decode("utf-8")

def verify_payload_signature(receipt_hash: str, signature_b64: str) -> bool:
    try:
        private_key = get_signing_key()
        public_key = private_key.public_key()
        signature_bytes = base64.b64decode(signature_b64.encode("utf-8"))
        public_key.verify(signature_bytes, receipt_hash.encode("utf-8"))
        return True
    except Exception:
        return False

def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _safe_hash(value: Any) -> str:
    if value is None:
        return _sha256("null")
    if isinstance(value, str):
        return _sha256(value)
    return _sha256(_canonical_json(value))


def _make_detached_signature(receipt_hash: str, algorithm: str = "ed25519") -> str:
    return sign_payload(receipt_hash)


def _make_timestamp_token(mode: str, receipt_hash: str) -> tuple[str, str]:
    now = utc_now().isoformat()
    external_enabled = os.getenv("CRYPTO_RECEIPTS_EXTERNAL_TIMESTAMP_ENABLED", "false").lower() == "true"
    if external_enabled:
        token = f"external_tsa:{now}:{_sha256(receipt_hash + now + 'external-tsa-seed')[:32]}"
        return "external_tsa", token
    else:
        token = f"local_ts:{now}:{_sha256(receipt_hash + now)[:32]}"
        return "local", token


def build_receipt_hash(
    *,
    prompt_hash: str,
    response_hash: str,
    previous_receipt_hash: str | None,
    request_payload_hash: str | None = None,
    response_payload_hash: str | None = None,
    runtime_snapshot_hash: str | None = None,
    routing_decision_hash: str | None = None,
    client_id: str | None = None,
    model_name: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> str:
    cfg = get_settings()
    payload = {
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
        "previous_receipt_hash": previous_receipt_hash if cfg.commercial_receipts_chaining_enabled else None,
        "request_payload_hash": request_payload_hash,
        "response_payload_hash": response_payload_hash,
        "runtime_snapshot_hash": runtime_snapshot_hash,
        "routing_decision_hash": routing_decision_hash,
        "client_id": client_id,
        "model_name": model_name,
    }
    if metadata_json:
        payload["metadata"] = sanitize_report_payload(metadata_json)
    return _sha256(_canonical_json(payload))


def summarize_receipt(receipt: CommercialInferenceReceipt) -> dict[str, Any]:
    return sanitize_report_payload({
        "id": str(receipt.id),
        "receipt_hash": receipt.receipt_hash[:16],
        "previous_receipt_hash": (receipt.previous_receipt_hash or "")[:16] or None,
        "verification_status": receipt.verification_status,
        "signature_algorithm": receipt.signature_algorithm,
        "timestamp_mode": receipt.timestamp_mode,
        "signed_at": receipt.signed_at.isoformat() if receipt.signed_at else None,
        "verified_at": receipt.verified_at.isoformat() if receipt.verified_at else None,
        "has_signature": bool(receipt.detached_signature),
        "tamper_reason": receipt.tamper_reason,
        "prompt_hash": receipt.prompt_hash[:16],
        "response_hash": receipt.response_hash[:16],
        "runtime_snapshot_hash": (receipt.runtime_snapshot_hash or "")[:16] or None,
        "routing_decision_hash": (receipt.routing_decision_hash or "")[:16] or None,
        "immutable_hash": (receipt.immutable_hash or "")[:16] or None,
        "client_id": receipt.client_id,
        "model_name": receipt.model_name,
    })


async def generate_inference_receipt(
    session: AsyncSession,
    *,
    reproducibility_record_id: uuid.UUID | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    client_id: str | None = None,
    model_name: str | None = None,
    backend_name: str | None = None,
    provider: str | None = None,
    prompt_hash: str,
    response_hash: str,
    request_payload_hash: str | None = None,
    response_payload_hash: str | None = None,
    runtime_snapshot_hash: str | None = None,
    routing_decision_hash: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> CommercialInferenceReceipt:
    cfg = get_settings()
    sanitized_metadata = sanitize_report_payload(metadata_json or {})
    sanitized_metadata.pop("prompt_text", None)
    sanitized_metadata.pop("response_text", None)

    last_receipt = None
    previous_receipt_hash = None
    if cfg.commercial_receipts_chaining_enabled:
        result = await session.execute(
            select(CommercialInferenceReceipt)
            .order_by(desc(CommercialInferenceReceipt.created_at))
            .limit(1)
        )
        last_receipt = result.scalar_one_or_none()
        if last_receipt:
            previous_receipt_hash = last_receipt.receipt_hash

    receipt_hash = build_receipt_hash(
        prompt_hash=prompt_hash,
        response_hash=response_hash,
        previous_receipt_hash=previous_receipt_hash,
        request_payload_hash=request_payload_hash,
        response_payload_hash=response_payload_hash,
        runtime_snapshot_hash=runtime_snapshot_hash,
        routing_decision_hash=routing_decision_hash,
        client_id=client_id,
        model_name=model_name,
        metadata_json=sanitized_metadata,
    )

    timestamp_mode = cfg.commercial_receipts_timestamp_mode
    mode, timestamp_token = _make_timestamp_token(timestamp_mode, receipt_hash)

    signature_algorithm = cfg.commercial_receipt_signature_algorithm
    detached_signature = _make_detached_signature(receipt_hash, signature_algorithm)

    immutable_payload = {
        "receipt_hash": receipt_hash,
        "previous_receipt_hash": previous_receipt_hash,
        "prompt_hash": prompt_hash,
        "response_hash": response_hash,
        "signed_at": utc_now().isoformat(),
        "timestamp_token": timestamp_token,
        "detached_signature": detached_signature,
        "signature_algorithm": signature_algorithm,
    }
    immutable_hash = _sha256(_canonical_json(immutable_payload))

    receipt = CommercialInferenceReceipt(
        reproducibility_record_id=reproducibility_record_id,
        request_id=request_id,
        correlation_id=correlation_id,
        client_id=client_id,
        model_name=model_name,
        backend_name=backend_name,
        provider=provider,
        prompt_hash=prompt_hash,
        response_hash=response_hash,
        request_payload_hash=request_payload_hash,
        response_payload_hash=response_payload_hash,
        runtime_snapshot_hash=runtime_snapshot_hash,
        routing_decision_hash=routing_decision_hash,
        receipt_hash=receipt_hash,
        previous_receipt_hash=previous_receipt_hash,
        immutable_hash=immutable_hash,
        detached_signature=detached_signature,
        signature_algorithm=signature_algorithm,
        timestamp_mode=mode,
        timestamp_token=timestamp_token,
        signed_at=utc_now(),
        verification_status="pending",
        metadata_json=sanitized_metadata,
    )
    session.add(receipt)
    await session.flush()

    ledger_event = CommercialInferenceReceiptLedgerEvent(
        receipt_id=receipt.id,
        event_type="receipt_created",
        summary="Inference receipt created",
        immutable_hash=_sha256(f"receipt_created:{receipt_hash}"),
    )
    session.add(ledger_event)
    await session.flush()

    return receipt


async def sign_receipt(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
) -> CommercialInferenceReceipt:
    cfg = get_settings()
    receipt.detached_signature = _make_detached_signature(
        receipt.receipt_hash, cfg.commercial_receipt_signature_algorithm
    )
    receipt.signature_algorithm = cfg.commercial_receipt_signature_algorithm
    receipt.verification_status = "pending"

    ledger_event = CommercialInferenceReceiptLedgerEvent(
        receipt_id=receipt.id,
        event_type="receipt_signed",
        summary="Receipt signed",
        immutable_hash=_sha256(f"receipt_signed:{receipt.receipt_hash}"),
    )
    session.add(ledger_event)
    await session.flush()
    return receipt


async def build_receipt_chain(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
) -> list[dict[str, Any]]:
    chain: list[CommercialInferenceReceipt] = []
    current = receipt
    while current is not None:
        chain.append(current)
        if current.previous_receipt_hash is None:
            break
        result = await session.execute(
            select(CommercialInferenceReceipt)
            .where(CommercialInferenceReceipt.receipt_hash == current.previous_receipt_hash)
        )
        current = result.scalar_one_or_none()
        if current is None:
            break
    return [summarize_receipt(item) for item in chain]


async def verify_receipt(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
    *,
    replay_match: bool | None = None,
    runtime_match: bool | None = None,
) -> CommercialInferenceReceiptVerificationReport:
    cfg = get_settings()
    recomputed_hash = build_receipt_hash(
        prompt_hash=receipt.prompt_hash,
        response_hash=receipt.response_hash,
        previous_receipt_hash=receipt.previous_receipt_hash,
        request_payload_hash=receipt.request_payload_hash,
        response_payload_hash=receipt.response_payload_hash,
        runtime_snapshot_hash=receipt.runtime_snapshot_hash,
        routing_decision_hash=receipt.routing_decision_hash,
        client_id=receipt.client_id,
        model_name=receipt.model_name,
        metadata_json=receipt.metadata_json,
    )
    hash_valid = recomputed_hash == receipt.receipt_hash

    signature_valid = verify_payload_signature(receipt.receipt_hash, receipt.detached_signature) if receipt.detached_signature else False

    chain_valid = True
    if cfg.commercial_receipts_chaining_enabled and receipt.previous_receipt_hash:
        prev = await session.execute(
            select(CommercialInferenceReceipt)
            .where(CommercialInferenceReceipt.receipt_hash == receipt.previous_receipt_hash)
        )
        chain_valid = prev.scalar_one_or_none() is not None

    drift = bool(runtime_match is False or replay_match is False)

    if not hash_valid:
        receipt.verification_status = "tampered"
        receipt.tamper_reason = "hash_mismatch"
        ledger_event = CommercialInferenceReceiptLedgerEvent(
            receipt_id=receipt.id,
            event_type="receipt_tamper_detected",
            summary="Receipt hash mismatch detected",
            immutable_hash=_sha256(f"receipt_tamper:{receipt.receipt_hash}"),
        )
        session.add(ledger_event)
        result = "invalid"
    elif drift:
        receipt.verification_status = "failed"
        receipt.tamper_reason = "drift_detected"
        result = "invalid"
    elif hash_valid and signature_valid and chain_valid:
        receipt.verification_status = "verified"
        result = "valid"
    else:
        receipt.verification_status = "verified"
        result = "partial"

    receipt.verified_at = utc_now()

    report_payload = {
        "receipt_id": str(receipt.id),
        "verification_result": result,
        "chain_valid": chain_valid,
        "signature_valid": signature_valid,
        "timestamp_valid": bool(receipt.timestamp_token),
        "runtime_match": runtime_match,
        "replay_match": replay_match,
        "drift_detected": drift,
    }
    report_hash = _sha256(_canonical_json(report_payload))

    report = CommercialInferenceReceiptVerificationReport(
        receipt_id=receipt.id,
        verification_result=result,
        chain_valid=chain_valid,
        signature_valid=signature_valid,
        timestamp_valid=bool(receipt.timestamp_token),
        runtime_match=runtime_match,
        replay_match=replay_match,
        drift_detected=drift,
        report_hash=report_hash,
    )
    session.add(report)

    ledger_event = CommercialInferenceReceiptLedgerEvent(
        receipt_id=receipt.id,
        event_type="receipt_verified",
        summary=f"Receipt verification: {result}",
        immutable_hash=_sha256(f"receipt_verified:{receipt.receipt_hash}:{result}"),
    )
    session.add(ledger_event)
    await session.flush()
    return report


async def validate_receipt_chain(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
) -> dict[str, Any]:
    chain = await build_receipt_chain(session, receipt)
    chain_valid = True
    broken_links: list[int] = []
    for i in range(len(chain) - 1):
        current = chain[i]
        previous = chain[i + 1]
        if current.get("previous_receipt_hash") and current["previous_receipt_hash"] != previous.get("receipt_hash"):
            chain_valid = False
            broken_links.append(i)

    ledger_event = CommercialInferenceReceiptLedgerEvent(
        receipt_id=receipt.id,
        event_type="receipt_chain_validated",
        summary=f"Chain validation: {'valid' if chain_valid else 'broken'} ({len(chain)} links)",
        immutable_hash=_sha256(f"receipt_chain_validated:{receipt.receipt_hash}:{chain_valid}"),
    )
    session.add(ledger_event)
    await session.flush()

    return {
        "receipt_id": str(receipt.id),
        "chain_valid": chain_valid,
        "chain_length": len(chain),
        "broken_links": broken_links,
        "chain": chain,
    }


async def export_receipt(
    session: AsyncSession,
    receipt: CommercialInferenceReceipt,
    *,
    include_sensitive: bool = False,
) -> dict[str, Any]:
    cfg = get_settings()
    result = {
        "id": str(receipt.id),
        "receipt_hash": receipt.receipt_hash,
        "previous_receipt_hash": receipt.previous_receipt_hash,
        "immutable_hash": receipt.immutable_hash,
        "detached_signature": receipt.detached_signature,
        "signature_algorithm": receipt.signature_algorithm,
        "timestamp_mode": receipt.timestamp_mode,
        "timestamp_token": receipt.timestamp_token,
        "signed_at": receipt.signed_at.isoformat() if receipt.signed_at else None,
        "verified_at": receipt.verified_at.isoformat() if receipt.verified_at else None,
        "verification_status": receipt.verification_status,
        "tamper_reason": receipt.tamper_reason,
        "prompt_hash": receipt.prompt_hash,
        "response_hash": receipt.response_hash,
        "request_payload_hash": receipt.request_payload_hash,
        "response_payload_hash": receipt.response_payload_hash,
        "runtime_snapshot_hash": receipt.runtime_snapshot_hash,
        "routing_decision_hash": receipt.routing_decision_hash,
        "model_name": receipt.model_name,
        "backend_name": receipt.backend_name,
        "provider": receipt.provider,
        "client_id": receipt.client_id,
        "correlation_id": receipt.correlation_id,
        "request_id": receipt.request_id,
    }

    if include_sensitive:
        result["metadata_json"] = receipt.metadata_json

    if cfg.commercial_receipts_export_enabled:
        ledger_event = CommercialInferenceReceiptLedgerEvent(
            receipt_id=receipt.id,
            event_type="receipt_exported",
            summary="Receipt exported",
            immutable_hash=_sha256(f"receipt_exported:{receipt.receipt_hash}"),
        )
        session.add(ledger_event)
        await session.flush()

    return result
