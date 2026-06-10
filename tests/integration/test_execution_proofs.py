"""Tests for execution proof generation and verification."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.models.commercial.commercial_cryptographic_receipts import CommercialInferenceReceipt
from app.models.commercial.commercial_merkle_timelines import (
    CommercialExecutionProof,
    CommercialMerkleLeaf,
    CommercialMerkleTimeline,
)
from app.services.inference.execution_proofs import (
    _sanitize_metadata,
    export_execution_proof,
    generate_execution_proof,
    verify_execution_proof,
)
from app.services.inference.merkle_timelines import (
    canonical_leaf_hash,
    seal_timeline,
)


def test_sanitize_metadata_removes_sensitive_keys():
    metadata = {
        "client_id": "c1",
        "prompt": "secret prompt",
        "response": "secret response",
        "messages": ["m1"],
        "choices": [],
        "content": "x",
        "completion": "y",
    }
    sanitized = _sanitize_metadata(metadata)
    assert "prompt" not in sanitized
    assert "response" not in sanitized
    assert "messages" not in sanitized
    assert "choices" not in sanitized
    assert "content" not in sanitized
    assert "completion" not in sanitized
    assert sanitized["client_id"] == "c1"


@pytest.mark.asyncio
async def test_build_receipt_timeline_deterministic_root(session):
    # Create receipts
    for i in range(4):
        receipt = CommercialInferenceReceipt(
            id=uuid4(),
            client_id="client-1",
            model_name="m1",
            prompt_hash=hashlib.sha256(f"p{i}".encode()).hexdigest(),
            response_hash=hashlib.sha256(f"r{i}".encode()).hexdigest(),
            receipt_hash=hashlib.sha256(f"receipt{i}".encode()).hexdigest(),
            signed_at=datetime.now(timezone.utc),
            timestamp_mode="local",
            verification_status="valid",
        )
        session.add(receipt)
    await session.commit()

    from app.services.inference.execution_proofs import build_receipt_timeline

    end = datetime.now(timezone.utc)
    start = end.replace(hour=end.hour - 1)
    timeline = await build_receipt_timeline(session, start, end)
    assert timeline.leaf_count == 4
    assert len(timeline.merkle_root) == 64
    assert timeline.timeline_type == "inference_receipts"


@pytest.mark.asyncio
async def test_build_receipt_timeline_empty_raises(session):
    from app.services.inference.execution_proofs import build_receipt_timeline
    from app.services.inference.merkle_timelines import MerkleError

    end = datetime.now(timezone.utc)
    start = end.replace(year=end.year - 10)
    with pytest.raises(MerkleError):
        await build_receipt_timeline(session, start, end)


@pytest.mark.asyncio
async def test_generate_execution_proof(session):
    receipt = CommercialInferenceReceipt(
        id=uuid4(),
        client_id="client-1",
        model_name="m1",
        prompt_hash=hashlib.sha256(b"p1").hexdigest(),
        response_hash=hashlib.sha256(b"r1").hexdigest(),
        receipt_hash=hashlib.sha256(b"receipt1").hexdigest(),
        signed_at=datetime.now(timezone.utc),
        timestamp_mode="local",
        verification_status="valid",
        runtime_snapshot_hash=hashlib.sha256(b"snap").hexdigest(),
    )
    session.add(receipt)
    await session.commit()

    leaf_hash = canonical_leaf_hash(str(receipt.id), "inference_receipt", _sanitize_metadata({
        "client_id": "client-1",
        "model_name": "m1",
    }))
    timeline = CommercialMerkleTimeline(
        id=uuid4(),
        timeline_type="inference_receipts",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        leaf_count=1,
        merkle_root=seal_timeline([leaf_hash]),
        timeline_hash=seal_timeline([leaf_hash]),
        status="sealed",
    )
    session.add(timeline)
    leaf = CommercialMerkleLeaf(
        id=uuid4(),
        timeline_id=timeline.id,
        source_type="inference_receipt",
        source_id=str(receipt.id),
        leaf_hash=leaf_hash,
        leaf_index=0,
        metadata_json={},
    )
    session.add(leaf)
    await session.commit()

    proof = await generate_execution_proof(session, timeline, receipt, [leaf])
    assert proof.proof_hash is not None
    assert len(proof.proof_hash) == 64
    assert proof.proof_json["receipt_hash"] == receipt.receipt_hash
    assert proof.proof_json["timeline_root"] == timeline.merkle_root
    assert proof.proof_json["merkle_inclusion_proof"] is not None
    assert "prompt" not in str(proof.proof_json)
    assert "response" not in str(proof.proof_json)


@pytest.mark.asyncio
async def test_generate_execution_proof_receipt_not_found(session):
    receipt = CommercialInferenceReceipt(
        id=uuid4(),
        client_id="client-1",
        model_name="m1",
        prompt_hash=hashlib.sha256(b"p1").hexdigest(),
        response_hash=hashlib.sha256(b"r1").hexdigest(),
        receipt_hash=hashlib.sha256(b"receipt1").hexdigest(),
        signed_at=datetime.now(timezone.utc),
        timestamp_mode="local",
        verification_status="valid",
    )
    timeline = CommercialMerkleTimeline(
        id=uuid4(),
        timeline_type="inference_receipts",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        leaf_count=0,
        merkle_root=hashlib.sha256(b"root").hexdigest(),
        timeline_hash=hashlib.sha256(b"root").hexdigest(),
        status="sealed",
    )
    from app.services.inference.merkle_timelines import MerkleError

    with pytest.raises(MerkleError):
        await generate_execution_proof(session, timeline, receipt, [])


@pytest.mark.asyncio
async def test_verify_execution_proof_valid(session):
    receipt = CommercialInferenceReceipt(
        id=uuid4(),
        client_id="client-1",
        model_name="m1",
        prompt_hash=hashlib.sha256(b"p1").hexdigest(),
        response_hash=hashlib.sha256(b"r1").hexdigest(),
        receipt_hash=hashlib.sha256(b"receipt1").hexdigest(),
        signed_at=datetime.now(timezone.utc),
        timestamp_mode="local",
        verification_status="valid",
    )
    session.add(receipt)

    leaf_hash = canonical_leaf_hash(str(receipt.id), "inference_receipt", {})
    timeline = CommercialMerkleTimeline(
        id=uuid4(),
        timeline_type="inference_receipts",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        leaf_count=1,
        merkle_root=seal_timeline([leaf_hash]),
        timeline_hash=seal_timeline([leaf_hash]),
        status="sealed",
    )
    session.add(timeline)
    leaf = CommercialMerkleLeaf(
        id=uuid4(),
        timeline_id=timeline.id,
        source_type="inference_receipt",
        source_id=str(receipt.id),
        leaf_hash=leaf_hash,
        leaf_index=0,
        metadata_json={},
    )
    session.add(leaf)
    await session.commit()

    proof = await generate_execution_proof(session, timeline, receipt, [leaf])
    session.add(proof)
    await session.commit()

    valid = await verify_execution_proof(session, proof)
    assert valid is True


@pytest.mark.asyncio
async def test_verify_execution_proof_invalid_after_tamper(session):
    # Use 4 receipts so the Merkle tree has sibling steps to tamper with
    receipt_ids = [uuid4() for _ in range(4)]
    target_receipt = CommercialInferenceReceipt(
        id=receipt_ids[0],
        client_id="client-1",
        model_name="m1",
        prompt_hash=hashlib.sha256(b"p1").hexdigest(),
        response_hash=hashlib.sha256(b"r1").hexdigest(),
        receipt_hash=hashlib.sha256(b"receipt1").hexdigest(),
        signed_at=datetime.now(timezone.utc),
        timestamp_mode="local",
        verification_status="valid",
    )
    session.add(target_receipt)

    leaf_hashes = [
        canonical_leaf_hash(str(rid), "inference_receipt", {})
        for rid in receipt_ids
    ]
    timeline = CommercialMerkleTimeline(
        id=uuid4(),
        timeline_type="inference_receipts",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        leaf_count=4,
        merkle_root=seal_timeline(leaf_hashes),
        timeline_hash=seal_timeline(leaf_hashes),
        status="sealed",
    )
    session.add(timeline)
    leaves = []
    for idx, (rid, lh) in enumerate(zip(receipt_ids, leaf_hashes)):
        leaf = CommercialMerkleLeaf(
            id=uuid4(),
            timeline_id=timeline.id,
            source_type="inference_receipt",
            source_id=str(rid),
            leaf_hash=lh,
            leaf_index=idx,
            metadata_json={},
        )
        session.add(leaf)
        leaves.append(leaf)
    await session.commit()

    proof = await generate_execution_proof(session, timeline, target_receipt, leaves)
    # Tamper with the first sibling hash in the inclusion proof
    proof.proof_json["merkle_inclusion_proof"]["steps"][0]["sibling_hash"] = hashlib.sha256(b"tamper").hexdigest()
    session.add(proof)
    await session.commit()

    valid = await verify_execution_proof(session, proof)
    assert valid is False


@pytest.mark.asyncio
async def test_export_execution_proof_no_sensitive_data(session):
    proof = CommercialExecutionProof(
        id=uuid4(),
        timeline_id=uuid4(),
        receipt_id=uuid4(),
        proof_type="execution",
        proof_json={
            "receipt_hash": "abc123",
            "timeline_root": "root123",
            "previous_timeline_root": None,
            "merkle_inclusion_proof": {"leaf_hash": "leaf123", "steps": []},
            "runtime_snapshot_hash": "snap123",
            "model_manifest_hash": "manifest123",
            "replay_verification_summary": {"chain_valid": True},
            "timestamp_summary": {"signed_at": "2026-01-01T00:00:00Z"},
            "prompt": "should-be-removed",
            "response": "should-be-removed",
        },
        proof_hash=hashlib.sha256(b"proof").hexdigest(),
        verification_status="pending",
    )
    exported = await export_execution_proof(proof)
    assert "proof_hash" in exported
    assert "timeline_root" in exported
    assert "prompt" not in exported
    assert "response" not in exported
    assert "merkle_inclusion_proof" in exported
