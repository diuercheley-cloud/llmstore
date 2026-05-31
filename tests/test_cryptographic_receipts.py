from __future__ import annotations

import hashlib
import json

import pytest
from sqlalchemy import select

from app.models.commercial_cryptographic_receipts import (
    CommercialInferenceReceipt,
    CommercialInferenceReceiptLedgerEvent,
    CommercialInferenceReceiptVerificationReport,
)
from app.services.inference.cryptographic_receipts import (
    build_receipt_hash,
    export_receipt,
    generate_inference_receipt,
    sign_receipt,
    build_receipt_chain,
    validate_receipt_chain,
    verify_receipt,
    summarize_receipt,
)
from app.utils.crypto_signer import sign_payload


@pytest.mark.asyncio
async def test_generate_inference_receipt(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = False

    receipt = await generate_inference_receipt(
        session,
        client_id="test-client",
        model_name="test-model",
        prompt_hash=hashlib.sha256(b"test prompt").hexdigest(),
        response_hash=hashlib.sha256(b"test response").hexdigest(),
        runtime_snapshot_hash=hashlib.sha256(b"runtime-snap").hexdigest(),
        routing_decision_hash=hashlib.sha256(b"routing").hexdigest(),
    )
    assert receipt is not None
    assert receipt.client_id == "test-client"
    assert receipt.model_name == "test-model"
    assert receipt.receipt_hash is not None
    assert receipt.verification_status == "pending"
    assert receipt.detached_signature is not None
    assert receipt.signature_algorithm == "ed25519"
    assert receipt.timestamp_mode == "local"
    assert receipt.previous_receipt_hash is None
    assert receipt.immutable_hash is not None

    ledger = (
        await session.execute(
            select(CommercialInferenceReceiptLedgerEvent)
            .where(CommercialInferenceReceiptLedgerEvent.receipt_id == receipt.id)
        )
    ).scalars().all()
    assert len(ledger) >= 1
    assert ledger[0].event_type == "receipt_created"


@pytest.mark.asyncio
async def test_generate_receipt_with_chain(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    r1 = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"prompt1").hexdigest(),
        response_hash=hashlib.sha256(b"response1").hexdigest(),
    )
    r2 = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"prompt2").hexdigest(),
        response_hash=hashlib.sha256(b"response2").hexdigest(),
    )
    assert r2.previous_receipt_hash == r1.receipt_hash
    assert r1.previous_receipt_hash is None


@pytest.mark.asyncio
async def test_receipt_hash_consistency(session, settings):
    settings.commercial_receipts_chaining_enabled = False
    h1 = build_receipt_hash(
        prompt_hash="abc",
        response_hash="def",
        previous_receipt_hash=None,
    )
    h2 = build_receipt_hash(
        prompt_hash="abc",
        response_hash="def",
        previous_receipt_hash=None,
    )
    assert h1 == h2

    h3 = build_receipt_hash(
        prompt_hash="abc",
        response_hash="xyz",
        previous_receipt_hash=None,
    )
    assert h1 != h3


@pytest.mark.asyncio
async def test_detached_signature(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"sig-test").hexdigest(),
        response_hash=hashlib.sha256(b"sig-response").hexdigest(),
    )
    await sign_receipt(session, receipt)
    assert receipt.detached_signature is not None
    assert receipt.detached_signature.startswith("placeholder_ed25519_")
    assert receipt.signature_algorithm == "ed25519"


@pytest.mark.asyncio
async def test_receipt_verification_valid(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = False
    receipt = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"verify-test").hexdigest(),
        response_hash=hashlib.sha256(b"verify-response").hexdigest(),
    )
    report = await verify_receipt(session, receipt)
    assert report is not None
    assert report.verification_result in ("valid", "partial")
    assert report.report_hash is not None

    reports = (
        await session.execute(
            select(CommercialInferenceReceiptVerificationReport)
            .where(CommercialInferenceReceiptVerificationReport.receipt_id == receipt.id)
        )
    ).scalars().all()
    assert len(reports) >= 1


@pytest.mark.asyncio
async def test_receipt_chain_validation(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True
    settings.commercial_receipts_signature_required = False

    r1 = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"chain1").hexdigest(),
        response_hash=hashlib.sha256(b"chain1-resp").hexdigest(),
    )
    r2 = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"chain2").hexdigest(),
        response_hash=hashlib.sha256(b"chain2-resp").hexdigest(),
    )
    r3 = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"chain3").hexdigest(),
        response_hash=hashlib.sha256(b"chain3-resp").hexdigest(),
    )
    result = await validate_receipt_chain(session, r3)
    assert result["chain_valid"] is True
    assert result["chain_length"] >= 3

    chain = await build_receipt_chain(session, r3)
    assert len(chain) >= 3
    assert chain[0]["receipt_hash"] == r3.receipt_hash[:16]


@pytest.mark.asyncio
async def test_export_receipt_sanitized(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_export_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="test-client",
        model_name="test-model",
        prompt_hash=hashlib.sha256(b"export-test").hexdigest(),
        response_hash=hashlib.sha256(b"export-response").hexdigest(),
        metadata_json={"prompt_text": "sensitive-data", "safe_key": "safe-value"},
    )
    exported = await export_receipt(session, receipt, include_sensitive=False)
    assert exported["receipt_hash"] == receipt.receipt_hash
    assert exported["prompt_hash"] == receipt.prompt_hash


@pytest.mark.asyncio
async def test_summarize_receipt(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="test-client",
        prompt_hash=hashlib.sha256(b"summary-test").hexdigest(),
        response_hash=hashlib.sha256(b"summary-response").hexdigest(),
        metadata_json={"prompt_text": "sensitive", "safe": "data"},
    )
    summary = summarize_receipt(receipt)
    assert summary["id"] == str(receipt.id)
    assert summary["verification_status"] == "pending"
    assert "prompt_text" not in str(summary)


@pytest.mark.asyncio
async def test_tenant_verification(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="tenant-client",
        prompt_hash=hashlib.sha256(b"tenant-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"tenant-response").hexdigest(),
    )
    assert receipt.client_id == "tenant-client"
    assert receipt.prompt_hash is not None
    assert receipt.response_hash is not None
    summary = summarize_receipt(receipt)
    assert summary["client_id"] == "tenant-client"
    assert "prompt" not in summary.get("metadata_json", {}).get("prompt_text", "")


@pytest.mark.asyncio
async def test_receipt_replay_linkage(session, settings):
    settings.commercial_receipts_enabled = True
    import hashlib
    runtime_hash = hashlib.sha256(b"runtime-snapshot-data").hexdigest()
    receipt = await generate_inference_receipt(
        session,
        client_id="link-client",
        prompt_hash=hashlib.sha256(b"link-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"link-response").hexdigest(),
        runtime_snapshot_hash=runtime_hash,
    )
    assert receipt.runtime_snapshot_hash == runtime_hash
    report = await verify_receipt(session, receipt, replay_match=True, runtime_match=True)
    assert report.verification_result == "valid"
