from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...core.config import get_settings
from ...models.commercial.commercial_attestation import (
    CommercialPublicAttestationRequest,
    CommercialPublicAttestationResult,
)
from ...models.commercial.commercial_cryptographic_receipts import CommercialInferenceReceipt
from ...models.commercial.commercial_merkle_timelines import CommercialMerkleTimeline
from ...models.commercial.commercial_retrieval_proofs import (
    CommercialRetrievalProof,
    CommercialRetrievalReplayRecord,
)
from ...services.inference import witness_federation
from ...services.rag.retrieval_proofs import verify_lineage_consistency, verify_retrieval_proof


async def log_attestation_request(
    db: AsyncSession,
    request_hash: str,
    proof_hash: Optional[str] = None,
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None
) -> CommercialPublicAttestationRequest:
    # Mask IP for privacy
    masked_ip = ".".join(source_ip.split(".")[:2]) + ".x.x" if source_ip else None
    
    request = CommercialPublicAttestationRequest(
        request_hash=request_hash,
        submitted_proof_hash=proof_hash,
        source_ip=masked_ip,
        user_agent=user_agent[:511] if user_agent else None,
        status="received"
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request

async def verify_public_receipt(db: AsyncSession, receipt_hash: str) -> dict:
    result = await db.execute(select(CommercialInferenceReceipt).where(CommercialInferenceReceipt.receipt_hash == receipt_hash))
    receipt = result.scalar_one_or_none()
    
    if not receipt:
        return {"status": "invalid", "message": "Receipt not found in immutable ledger"}
        
    return {
        "status": "valid",
        "receipt_id": str(receipt.id),
        "timestamp": receipt.signed_at.isoformat(),
        "verification_status": receipt.verification_status,
        "signature_present": receipt.detached_signature is not None
    }

async def verify_public_timeline(db: AsyncSession, timeline_root: str) -> dict:
    result = await db.execute(select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.merkle_root == timeline_root))
    timeline = result.scalar_one_or_none()
    
    if not timeline:
        return {"status": "invalid", "message": "Timeline root not found"}
        
    return {
        "status": "valid",
        "timeline_id": str(timeline.id),
        "type": timeline.timeline_type,
        "period_start": timeline.period_start.isoformat(),
        "period_end": timeline.period_end.isoformat(),
        "leaf_count": timeline.leaf_count,
        "sealed": timeline.status == "sealed"
    }

async def verify_public_witness_quorum(db: AsyncSession, timeline_root: str) -> dict:
    timeline_res = await db.execute(select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.merkle_root == timeline_root))
    timeline = timeline_res.scalar_one_or_none()
    
    if not timeline:
        return {"status": "invalid", "message": "Timeline not found"}
        
    quorum = await witness_federation.evaluate_witness_quorum(db, timeline.id)
    return sanitize_public_result(quorum)


async def verify_public_retrieval_proof(db: AsyncSession, proof_hash: str) -> dict:
    result = await db.execute(select(CommercialRetrievalProof).where(CommercialRetrievalProof.proof_hash == proof_hash))
    proof = result.scalar_one_or_none()
    if not proof:
        return {"status": "invalid", "message": "Retrieval proof not found"}
    verified = await verify_retrieval_proof(db, proof)
    return sanitize_public_result(
        {
            "status": "valid" if verified["valid"] else "invalid",
            "proof_hash": proof.proof_hash,
            "timeline_root": proof.merkle_root,
            "lineage_root_hash": proof.lineage_root_hash,
            "verification": verified,
        }
    )


async def verify_public_lineage_consistency(db: AsyncSession, proof_hash: str) -> dict:
    result = await db.execute(select(CommercialRetrievalProof).where(CommercialRetrievalProof.proof_hash == proof_hash))
    proof = result.scalar_one_or_none()
    if not proof:
        return {"status": "invalid", "message": "Retrieval proof not found"}
    valid = await verify_lineage_consistency(db, proof)
    return sanitize_public_result(
        {
            "status": "valid" if valid else "invalid",
            "proof_hash": proof.proof_hash,
            "lineage_root_hash": proof.lineage_root_hash,
        }
    )


async def verify_public_retrieval_replay(db: AsyncSession, proof_hash: str) -> dict:
    result = await db.execute(select(CommercialRetrievalProof).where(CommercialRetrievalProof.proof_hash == proof_hash))
    proof = result.scalar_one_or_none()
    if not proof:
        return {"status": "invalid", "message": "Retrieval proof not found"}
    replay_result = await db.execute(
        select(CommercialRetrievalReplayRecord)
        .where(CommercialRetrievalReplayRecord.retrieval_proof_id == proof.id)
        .order_by(CommercialRetrievalReplayRecord.created_at.desc())
        .limit(1)
    )
    replay = replay_result.scalar_one_or_none()
    if replay is None:
        return {"status": "invalid", "message": "No retrieval replay found"}
    return sanitize_public_result(
        {
            "status": "valid" if replay.replay_status in {"matched", "drift_detected"} else "invalid",
            "proof_hash": proof.proof_hash,
            "replay_status": replay.replay_status,
            "drift_status": replay.drift_status,
            "drift_score": replay.drift_score,
        }
    )

def sanitize_public_result(data: dict) -> dict:
    # Remove sensitive fields like internal IDs or raw secrets if they existed
    sanitized = data.copy()
    keys_to_remove = ["internal_id", "db_id", "raw_secret", "debug_info"]
    for key in keys_to_remove:
        if key in sanitized:
            del sanitized[key]
            
    # If it's a witness list, ensure only names and types are shown
    if "signatures" in sanitized:
        sanitized["signatures"] = [
            {
                "witness_type": s.get("witness_type", "unknown"),
                "status": "verified",
                "signed_at": s.get("signed_at")
            }
            for s in sanitized["signatures"]
        ]
        
    return sanitized

async def summarize_gateway_status(db: AsyncSession) -> dict:
    req_count_res = await db.execute(select(CommercialPublicAttestationRequest))
    reqs = req_count_res.scalars().all()
    
    valid_res = await db.execute(select(CommercialPublicAttestationResult).where(CommercialPublicAttestationResult.result == "valid"))
    valids = valid_res.scalars().all()
    
    return {
        "enabled": get_settings().commercial_public_attestation_gateway_enabled,
        "mode": get_settings().commercial_public_attestation_mode,
        "total_requests": len(reqs),
        "valid_results": len(valids),
        "rate_limit_rpm": get_settings().commercial_public_attestation_rate_limit_rpm
    }
