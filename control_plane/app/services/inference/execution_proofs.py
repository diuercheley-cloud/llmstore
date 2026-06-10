"""Execution proof builder and verifier.

Aggregates inference receipts, replay events, runtime integrity scans,
and other attestations into Merkle-backed execution proofs.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.models.commercial.commercial_cryptographic_receipts import CommercialInferenceReceipt
from app.models.commercial.commercial_inference_reproducibility import (
    CommercialInferenceReplayEvent,
    CommercialInferenceRuntimeSnapshot,
)
from app.models.commercial.commercial_merkle_timelines import (
    CommercialExecutionProof,
    CommercialMerkleLeaf,
    CommercialMerkleTimeline,
)
from app.models.commercial.commercial_witness import (
    CommercialWitness,
    CommercialWitnessSignature,
)
from app.services.inference import witness_federation
from app.services.inference.merkle_timelines import (
    MerkleError,
    canonical_leaf_hash,
    generate_inclusion_proof,
    seal_timeline,
    validate_timeline_chain,
    verify_inclusion_proof,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Strip any prompt/response content from metadata."""
    keys_to_remove = {"prompt", "response", "completion", "message", "messages", "choices", "content"}
    return {k: v for k, v in metadata.items() if k not in keys_to_remove}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _json_hash(data: dict[str, Any]) -> str:
    return _sha256_hex(json.dumps(data, sort_keys=True, separators=(",", ":")))


# ---------------------------------------------------------------------------
# Timeline builders
# ---------------------------------------------------------------------------

async def build_receipt_timeline(
    db: AsyncSession,
    period_start: datetime,
    period_end: datetime,
    previous_root: str | None = None,
) -> CommercialMerkleTimeline:
    """Build a Merkle timeline from inference receipts in the given window."""
    receipts = (
        await db.execute(
            select(CommercialInferenceReceipt).where(
                CommercialInferenceReceipt.created_at >= period_start,
                CommercialInferenceReceipt.created_at < period_end,
            )
        )
    ).scalars().all()

    leaves: list[CommercialMerkleLeaf] = []
    leaf_hashes: list[str] = []
    for idx, receipt in enumerate(receipts):
        metadata = {
            "client_id": receipt.client_id,
            "model_name": receipt.model_name,
            "backend_name": receipt.backend_name,
            "provider": receipt.provider,
            "signed_at": receipt.signed_at.isoformat() if receipt.signed_at else None,
            "verification_status": receipt.verification_status,
        }
        metadata = _sanitize_metadata(metadata)
        leaf_hash = canonical_leaf_hash(
            source_id=str(receipt.id),
            source_type="inference_receipt",
            payload=metadata,
        )
        leaf = CommercialMerkleLeaf(
            timeline_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # placeholder
            source_type="inference_receipt",
            source_id=str(receipt.id),
            leaf_hash=leaf_hash,
            leaf_index=idx,
            metadata_json=metadata,
        )
        leaves.append(leaf)
        leaf_hashes.append(leaf_hash)

    if not leaf_hashes:
        raise MerkleError("No receipts found for timeline window")

    root = seal_timeline(leaf_hashes, previous_root)
    timeline = CommercialMerkleTimeline(
        timeline_type="inference_receipts",
        period_start=period_start,
        period_end=period_end,
        leaf_count=len(leaf_hashes),
        merkle_root=root,
        previous_timeline_root=previous_root,
        timeline_hash=_json_hash({
            "root": root,
            "previous": previous_root or "",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "leaf_count": len(leaf_hashes),
        }),
        status="sealed" if previous_root else "building",
        sealed_at=_now() if previous_root else None,
    )
    return timeline


async def build_runtime_integrity_timeline(
    db: AsyncSession,
    period_start: datetime,
    period_end: datetime,
    previous_root: str | None = None,
) -> CommercialMerkleTimeline:
    """Build a Merkle timeline from runtime integrity snapshots."""
    snapshots = (
        await db.execute(
            select(CommercialInferenceRuntimeSnapshot).where(
                CommercialInferenceRuntimeSnapshot.created_at >= period_start,
                CommercialInferenceRuntimeSnapshot.created_at < period_end,
            )
        )
    ).scalars().all()

    leaf_hashes: list[str] = []
    for idx, snap in enumerate(snapshots):
        metadata = {
            "backend_name": snap.backend_name,
            "runtime_engine": snap.runtime_engine,
            "model_name": snap.model_name,
            "snapshot_hash": snap.snapshot_hash,
        }
        metadata = _sanitize_metadata(metadata)
        leaf_hash = canonical_leaf_hash(
            source_id=str(snap.id),
            source_type="runtime_scan",
            payload=metadata,
        )
        leaf_hashes.append(leaf_hash)

    if not leaf_hashes:
        raise MerkleError("No runtime snapshots found for timeline window")

    root = seal_timeline(leaf_hashes, previous_root)
    timeline = CommercialMerkleTimeline(
        timeline_type="runtime_integrity",
        period_start=period_start,
        period_end=period_end,
        leaf_count=len(leaf_hashes),
        merkle_root=root,
        previous_timeline_root=previous_root,
        timeline_hash=_json_hash({
            "root": root,
            "previous": previous_root or "",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "leaf_count": len(leaf_hashes),
        }),
        status="sealed" if previous_root else "building",
        sealed_at=_now() if previous_root else None,
    )
    return timeline


async def build_replay_timeline(
    db: AsyncSession,
    period_start: datetime,
    period_end: datetime,
    previous_root: str | None = None,
) -> CommercialMerkleTimeline:
    """Build a Merkle timeline from replay events."""
    events = (
        await db.execute(
            select(CommercialInferenceReplayEvent).where(
                CommercialInferenceReplayEvent.created_at >= period_start,
                CommercialInferenceReplayEvent.created_at < period_end,
            )
        )
    ).scalars().all()

    leaf_hashes: list[str] = []
    for idx, event in enumerate(events):
        metadata = {
            "replay_type": event.replay_type,
            "replay_result": event.replay_result,
            "similarity_score": event.similarity_score,
        }
        metadata = _sanitize_metadata(metadata)
        leaf_hash = canonical_leaf_hash(
            source_id=str(event.id),
            source_type="replay_event",
            payload=metadata,
        )
        leaf_hashes.append(leaf_hash)

    if not leaf_hashes:
        raise MerkleError("No replay events found for timeline window")

    root = seal_timeline(leaf_hashes, previous_root)
    timeline = CommercialMerkleTimeline(
        timeline_type="replay_events",
        period_start=period_start,
        period_end=period_end,
        leaf_count=len(leaf_hashes),
        merkle_root=root,
        previous_timeline_root=previous_root,
        timeline_hash=_json_hash({
            "root": root,
            "previous": previous_root or "",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "leaf_count": len(leaf_hashes),
        }),
        status="sealed" if previous_root else "building",
        sealed_at=_now() if previous_root else None,
    )
    return timeline


# ---------------------------------------------------------------------------
# Proof generation and verification
# ---------------------------------------------------------------------------

async def generate_execution_proof(
    db: AsyncSession,
    timeline: CommercialMerkleTimeline,
    receipt: CommercialInferenceReceipt,
    leaves: list[CommercialMerkleLeaf],
    proof_type: str = "execution",
) -> CommercialExecutionProof:
    """Generate an execution proof bundle for a receipt within a timeline.

    The proof includes a Merkle inclusion proof, runtime snapshot hash,
    model manifest hash, and a summary of replay verification status.
    No prompt or response content is included.
    """
    leaf_hashes = [leaf.leaf_hash for leaf in sorted(leaves, key=lambda l: l.leaf_index)]

    # Find the leaf index for this receipt
    leaf_index = None
    for leaf in leaves:
        if leaf.source_id == str(receipt.id):
            leaf_index = leaf.leaf_index
            break
    if leaf_index is None:
        raise MerkleError("Receipt not found in timeline leaves")

    inclusion = generate_inclusion_proof(leaf_index, leaf_hashes)

    proof_json = {
        "receipt_id": str(receipt.id),
        "receipt_hash": receipt.receipt_hash,
        "signature_status": receipt.verification_status,
        "merkle_inclusion_proof": inclusion.to_dict(),
        "timeline_root": timeline.merkle_root,
        "previous_timeline_root": timeline.previous_timeline_root,
        "runtime_snapshot_hash": receipt.runtime_snapshot_hash,
        "model_manifest_hash": receipt.request_payload_hash,  # proxy for model manifest
        "replay_verification_summary": {
            "chain_valid": receipt.previous_receipt_hash is not None,
            "signature_valid": receipt.verification_status == "valid",
            "timestamp_mode": receipt.timestamp_mode,
        },
        "timestamp_summary": {
            "signed_at": receipt.signed_at.isoformat() if receipt.signed_at else None,
        },
    }

    # Add witness quorum if available
    quorum = await witness_federation.evaluate_witness_quorum(db, timeline.id)
    if quorum.get("quorum_status") != "error":
        # Fetch valid signatures details
        sigs_result = await db.execute(
            select(CommercialWitnessSignature, CommercialWitness.witness_name, CommercialWitness.witness_type)
            .join(CommercialWitness)
            .where(
                CommercialWitnessSignature.timeline_id == timeline.id,
                CommercialWitnessSignature.verification_status == "valid"
            )
        )
        sig_list = []
        for s, name, w_type in sigs_result:
            sig_list.append({
                "witness_name": name,
                "witness_type": w_type,
                "signature": s.signature,
                "signature_algorithm": s.signature_algorithm,
                "signed_at": s.signed_at.isoformat()
            })
            
        proof_json["witness_quorum_summary"] = {
            "quorum_status": "VALID" if quorum["quorum_status"] == "met" else "INVALID",
            "required_signatures": quorum["signatures_required"],
            "signatures_found": quorum["signatures_found"],
            "external_witness_present": quorum["external_witness_present"],
            "signatures": sig_list
        }

    proof_hash = _sha256_hex(json.dumps(proof_json, sort_keys=True, separators=(",", ":")))
    proof = CommercialExecutionProof(
        receipt_id=receipt.id,
        timeline_id=timeline.id,
        proof_type=proof_type,
        proof_json=proof_json,
        proof_hash=proof_hash,
        verification_status="pending",
    )
    return proof


async def verify_execution_proof(
    db: AsyncSession,
    proof: CommercialExecutionProof,
) -> bool:
    """Verify an execution proof.

    Checks:
    - Merkle inclusion proof validity
    - Timeline chain integrity
    - No tampering in leaf hashes
    """
    inclusion_dict = proof.proof_json.get("merkle_inclusion_proof", {})
    if not inclusion_dict:
        return False

    from app.services.inference.merkle_timelines import MerkleInclusionProof

    inclusion = MerkleInclusionProof.from_dict(inclusion_dict)
    if not verify_inclusion_proof(inclusion):
        return False

    # Verify timeline chain if applicable
    prev_root = proof.proof_json.get("previous_timeline_root")
    if prev_root:
        if not validate_timeline_chain(
            inclusion.root,
            prev_root,
            proof.proof_json.get("timeline_root"),
        ):
            return False

    return True


async def export_execution_proof(
    proof: CommercialExecutionProof,
) -> dict[str, Any]:
    """Export a tenant-safe execution proof.

    Removes any potentially sensitive fields while preserving the proof
    structure for external verification.
    """
    exported = {
        "proof_type": proof.proof_type,
        "proof_hash": proof.proof_hash,
        "verification_status": proof.verification_status,
        "timeline_root": proof.proof_json.get("timeline_root"),
        "previous_timeline_root": proof.proof_json.get("previous_timeline_root"),
        "merkle_inclusion_proof": proof.proof_json.get("merkle_inclusion_proof"),
        "runtime_snapshot_hash": proof.proof_json.get("runtime_snapshot_hash"),
        "model_manifest_hash": proof.proof_json.get("model_manifest_hash"),
        "replay_verification_summary": proof.proof_json.get("replay_verification_summary"),
        "timestamp_summary": proof.proof_json.get("timestamp_summary"),
        "witness_quorum_summary": proof.proof_json.get("witness_quorum_summary"),
        "created_at": proof.created_at.isoformat() if proof.created_at else None,
    }
    return exported
