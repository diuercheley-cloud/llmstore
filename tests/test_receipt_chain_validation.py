from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import select

from app.models.commercial_cryptographic_receipts import (
    CommercialInferenceReceipt,
    CommercialInferenceReceiptLedgerEvent,
)
from app.services.inference.cryptographic_receipts import (
    build_receipt_chain,
    generate_inference_receipt,
    validate_receipt_chain,
)


@pytest.mark.asyncio
async def test_chain_validation_valid(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    r1 = await generate_inference_receipt(
        session,
        client_id="chain-test",
        prompt_hash=hashlib.sha256(b"chain-p1").hexdigest(),
        response_hash=hashlib.sha256(b"chain-r1").hexdigest(),
    )
    r2 = await generate_inference_receipt(
        session,
        client_id="chain-test",
        prompt_hash=hashlib.sha256(b"chain-p2").hexdigest(),
        response_hash=hashlib.sha256(b"chain-r2").hexdigest(),
    )
    r3 = await generate_inference_receipt(
        session,
        client_id="chain-test",
        prompt_hash=hashlib.sha256(b"chain-p3").hexdigest(),
        response_hash=hashlib.sha256(b"chain-r3").hexdigest(),
    )
    result = await validate_receipt_chain(session, r3)
    assert result["chain_valid"] is True
    assert result["chain_length"] == 3

    chain = await build_receipt_chain(session, r3)
    assert len(chain) == 3


@pytest.mark.asyncio
async def test_chain_linked_order(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    r1 = await generate_inference_receipt(
        session,
        client_id="chain-order",
        prompt_hash=hashlib.sha256(b"order-1").hexdigest(),
        response_hash=hashlib.sha256(b"order-1r").hexdigest(),
    )
    r2 = await generate_inference_receipt(
        session,
        client_id="chain-order",
        prompt_hash=hashlib.sha256(b"order-2").hexdigest(),
        response_hash=hashlib.sha256(b"order-2r").hexdigest(),
    )
    r3 = await generate_inference_receipt(
        session,
        client_id="chain-order",
        prompt_hash=hashlib.sha256(b"order-3").hexdigest(),
        response_hash=hashlib.sha256(b"order-3r").hexdigest(),
    )
    chain = await build_receipt_chain(session, r3)
    assert chain[0]["receipt_hash"] == r3.receipt_hash[:16]
    assert chain[1]["receipt_hash"] == r2.receipt_hash[:16]
    assert chain[2]["receipt_hash"] == r1.receipt_hash[:16]


@pytest.mark.asyncio
async def test_single_receipt_chain(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    receipt = await generate_inference_receipt(
        session,
        client_id="single-chain",
        prompt_hash=hashlib.sha256(b"single").hexdigest(),
        response_hash=hashlib.sha256(b"single-r").hexdigest(),
    )
    chain = await build_receipt_chain(session, receipt)
    assert len(chain) == 1
    assert chain[0]["receipt_hash"] == receipt.receipt_hash[:16]


@pytest.mark.asyncio
async def test_chain_ledger_events(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    receipt = await generate_inference_receipt(
        session,
        client_id="ledger-test",
        prompt_hash=hashlib.sha256(b"ledger-p").hexdigest(),
        response_hash=hashlib.sha256(b"ledger-r").hexdigest(),
    )
    await validate_receipt_chain(session, receipt)

    events = (
        await session.execute(
            select(CommercialInferenceReceiptLedgerEvent)
            .where(CommercialInferenceReceiptLedgerEvent.receipt_id == receipt.id)
        )
    ).scalars().all()
    event_types = [e.event_type for e in events]
    assert "receipt_created" in event_types
    assert "receipt_chain_validated" in event_types


@pytest.mark.asyncio
async def test_chain_no_previous_receipt(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    receipt = await generate_inference_receipt(
        session,
        client_id="first-in-chain",
        prompt_hash=hashlib.sha256(b"first").hexdigest(),
        response_hash=hashlib.sha256(b"first-r").hexdigest(),
    )
    assert receipt.previous_receipt_hash is None
    chain = await build_receipt_chain(session, receipt)
    assert len(chain) == 1


@pytest.mark.asyncio
async def test_chain_validation_multiple_separate_chains(session, settings):
    settings.commercial_receipts_enabled = True
    settings.commercial_receipts_chaining_enabled = True

    r1 = await generate_inference_receipt(
        session,
        client_id="chain-a",
        prompt_hash=hashlib.sha256(b"a1").hexdigest(),
        response_hash=hashlib.sha256(b"a1r").hexdigest(),
    )
    r2 = await generate_inference_receipt(
        session,
        client_id="chain-b",
        prompt_hash=hashlib.sha256(b"b1").hexdigest(),
        response_hash=hashlib.sha256(b"b1r").hexdigest(),
    )
    assert r2.previous_receipt_hash == r1.receipt_hash
