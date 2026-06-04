from __future__ import annotations

import hashlib

import pytest
from app.models.commercial_cryptographic_receipts import (
    CommercialInferenceReceiptVerificationReport,
)
from app.services.inference.cryptographic_receipts import generate_inference_receipt
from app.services.inference.receipt_verification import (
    detect_receipt_tampering,
    generate_verification_report,
    verify_receipt_hash,
    verify_receipt_signature,
    verify_receipt_timestamp,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_verify_signature_valid(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="sig-test",
        prompt_hash=hashlib.sha256(b"sig-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"sig-response").hexdigest(),
    )
    assert verify_receipt_signature(receipt) is True
    assert receipt.signature_algorithm == "ed25519"
    assert receipt.detached_signature is not None


@pytest.mark.asyncio
async def test_verify_hash_valid(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="hash-test",
        prompt_hash=hashlib.sha256(b"hash-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"hash-response").hexdigest(),
    )
    assert verify_receipt_hash(receipt) is True


@pytest.mark.asyncio
async def test_verify_timestamp(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_timestamp_mode = "local"
    receipt = await generate_inference_receipt(
        session,
        client_id="ts-test",
        prompt_hash=hashlib.sha256(b"ts-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"ts-response").hexdigest(),
    )
    assert receipt.timestamp_mode == "local"
    assert verify_receipt_timestamp(receipt) is True
    assert receipt.timestamp_token is not None


@pytest.mark.asyncio
async def test_detect_tampering_hash_mismatch(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="tamper-test",
        prompt_hash=hashlib.sha256(b"original-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"original-response").hexdigest(),
    )
    receipt.prompt_hash = hashlib.sha256(b"tampered-prompt").hexdigest()
    result = await detect_receipt_tampering(session, receipt)
    assert "hash_mismatch" in result["tamper_reasons"]
    assert receipt.verification_status == "tampered"
    assert receipt.tamper_reason is not None


@pytest.mark.asyncio
async def test_detect_tampering_signature_missing(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="sig-tamper",
        prompt_hash=hashlib.sha256(b"st-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"st-response").hexdigest(),
    )
    receipt.detached_signature = None
    receipt.signature_algorithm = None
    result = await detect_receipt_tampering(session, receipt)
    assert "signature_invalid" in result["tamper_reasons"]


@pytest.mark.asyncio
async def test_generate_verification_report_valid(session, settings):
    settings.commercial_receipts_enabled = True
    receipt = await generate_inference_receipt(
        session,
        client_id="report-test",
        prompt_hash=hashlib.sha256(b"report-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"report-response").hexdigest(),
    )
    report_data = await generate_verification_report(session, receipt)
    assert report_data["verification_result"] == "valid"
    assert report_data["signature_valid"] is True
    assert report_data["report_hash"] is not None

    reports = (
        await session.execute(
            select(CommercialInferenceReceiptVerificationReport)
            .where(CommercialInferenceReceiptVerificationReport.receipt_id == receipt.id)
        )
    ).scalars().all()
    assert len(reports) >= 1
    assert reports[0].verification_result == "valid"


@pytest.mark.asyncio
async def test_offline_tsa_timestamp_mode(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_timestamp_mode = "offline_tsa"
    receipt = await generate_inference_receipt(
        session,
        client_id="offline-tsa",
        prompt_hash=hashlib.sha256(b"offline-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"offline-response").hexdigest(),
    )
    assert receipt.timestamp_mode == "offline_tsa"
    assert receipt.timestamp_token is not None
    assert "offline_tsa:" in receipt.timestamp_token


@pytest.mark.asyncio
async def test_external_placeholder_timestamp(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_timestamp_mode = "external_placeholder"
    receipt = await generate_inference_receipt(
        session,
        client_id="ext-ts",
        prompt_hash=hashlib.sha256(b"ext-prompt").hexdigest(),
        response_hash=hashlib.sha256(b"ext-response").hexdigest(),
    )
    assert receipt.timestamp_mode == "external_placeholder"
    assert "external_placeholder:" in receipt.timestamp_token


@pytest.mark.asyncio
async def test_verify_receipt_chain_valid(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True
    r1 = await generate_inference_receipt(
        session,
        client_id="chain-verify",
        prompt_hash=hashlib.sha256(b"cv1").hexdigest(),
        response_hash=hashlib.sha256(b"cv1r").hexdigest(),
    )
    r2 = await generate_inference_receipt(
        session,
        client_id="chain-verify",
        prompt_hash=hashlib.sha256(b"cv2").hexdigest(),
        response_hash=hashlib.sha256(b"cv2r").hexdigest(),
    )
    from app.services.inference.cryptographic_receipts import build_receipt_chain
    from app.services.inference.receipt_verification import verify_receipt_chain

    chain = await build_receipt_chain(session, r2)
    result = verify_receipt_chain(chain)
    assert result["chain_valid"] is True
    assert result["chain_length"] >= 2
