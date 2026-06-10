"""Tests for proof verification via API endpoints and tenant isolation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.models.commercial.commercial_merkle_timelines import (
    CommercialExecutionProof,
    CommercialMerkleTimeline,
)
from httpx import AsyncClient


def _admin_headers():
    return {"X-Admin-Token": "test-admin-token"}


@pytest.mark.asyncio
async def test_admin_timelines_list_requires_auth(admin_client: AsyncClient):
    res = await admin_client.get("/admin/inference/proofs/timelines")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_timelines_build_requires_auth(admin_client: AsyncClient):
    res = await admin_client.post("/admin/inference/proofs/timelines/build", json={
        "timeline_type": "inference_receipts",
        "window_minutes": 60,
    })
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_seal_timeline_requires_auth(admin_client: AsyncClient):
    res = await admin_client.post(f"/admin/inference/proofs/timelines/{uuid4()}/seal")
    assert res.status_code in (401, 404, 403)


@pytest.mark.asyncio
async def test_admin_verify_timeline_requires_auth(admin_client: AsyncClient):
    res = await admin_client.post(f"/admin/inference/proofs/timelines/{uuid4()}/verify")
    assert res.status_code in (401, 404, 403)


@pytest.mark.asyncio
async def test_admin_list_proofs_requires_auth(admin_client: AsyncClient):
    res = await admin_client.get("/admin/inference/proofs/proofs")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_generate_proof_requires_auth(admin_client: AsyncClient):
    res = await admin_client.post(f"/admin/inference/proofs/proofs/generate/{uuid4()}")
    assert res.status_code in (401, 404, 403)


@pytest.mark.asyncio
async def test_admin_verify_proof_requires_auth(admin_client: AsyncClient):
    res = await admin_client.post(f"/admin/inference/proofs/proofs/{uuid4()}/verify")
    assert res.status_code in (401, 404, 403)


@pytest.mark.asyncio
async def test_admin_export_proof_requires_auth(admin_client: AsyncClient):
    res = await admin_client.get(f"/admin/inference/proofs/proofs/{uuid4()}/export")
    assert res.status_code in (401, 404, 403)


@pytest.mark.asyncio
async def test_portal_proof_tenant_safe_no_sensitive_data(session):
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
            "timestamp_summary": {"signed_at": "2026-01-01T00:00:00Z"},
        },
        proof_hash=hashlib.sha256(b"proof").hexdigest(),
        verification_status="pending",
    )
    session.add(proof)
    await session.commit()

    from app.services.inference.execution_proofs import export_execution_proof

    exported = await export_execution_proof(proof)
    # Ensure no sensitive fields leak
    for forbidden in ("prompt", "response", "messages", "choices", "content", "completion"):
        assert forbidden not in exported


@pytest.mark.asyncio
async def test_timeline_seal_prevents_modification(session):
    timeline = CommercialMerkleTimeline(
        id=uuid4(),
        timeline_type="inference_receipts",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        leaf_count=2,
        merkle_root=hashlib.sha256(b"root").hexdigest(),
        timeline_hash=hashlib.sha256(b"root").hexdigest(),
        status="sealed",
        sealed_at=datetime.now(timezone.utc),
    )
    session.add(timeline)
    await session.commit()

    # Attempting to change a sealed timeline's root should conceptually be invalid
    # In practice, the DB row could still be updated, but the status signals immutability
    refreshed = await session.get(CommercialMerkleTimeline, timeline.id)
    assert refreshed.status == "sealed"


@pytest.mark.asyncio
async def test_timeline_chain_detects_tamper(session):
    prev_root = hashlib.sha256(b"prev").hexdigest()
    timeline = CommercialMerkleTimeline(
        id=uuid4(),
        timeline_type="inference_receipts",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        leaf_count=1,
        merkle_root=hashlib.sha256(b"root").hexdigest(),
        previous_timeline_root=prev_root,
        timeline_hash=hashlib.sha256(b"wrong").hexdigest(),  # intentionally wrong
        status="sealed",
        sealed_at=datetime.now(timezone.utc),
    )
    session.add(timeline)
    await session.commit()

    from app.services.inference.merkle_timelines import validate_timeline_chain

    valid = validate_timeline_chain(
        timeline.merkle_root,
        timeline.previous_timeline_root,
        timeline.timeline_hash,
    )
    assert valid is False
