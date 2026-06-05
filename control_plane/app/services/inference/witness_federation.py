import hashlib
import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...core.config import get_settings
from ...models.commercial_merkle_timelines import CommercialMerkleTimeline
from ...models.commercial_witness import (
    CommercialWitness,
    CommercialWitnessAuditEvent,
    CommercialWitnessQuorumPolicy,
    CommercialWitnessSignature,
)


async def register_witness(
    db: AsyncSession,
    name: str,
    witness_type: str,
    public_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    trust_level: str = "medium",
    metadata: dict = {}
) -> CommercialWitness:
    witness = CommercialWitness(
        witness_name=name,
        witness_type=witness_type,
        public_key=public_key,
        endpoint=endpoint,
        trust_level=trust_level,
        metadata_json=metadata
    )
    db.add(witness)
    await db.commit()
    await db.refresh(witness)
    
    await record_witness_audit_event(
        db, 
        event_type="witness_registered",
        witness_id=witness.id,
        summary=f"Witness {name} registered as {witness_type}"
    )
    return witness

async def request_witness_signature(
    db: AsyncSession,
    timeline_id: uuid.UUID,
    witness_id: uuid.UUID
) -> Optional[CommercialWitnessSignature]:
    timeline_result = await db.execute(select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.id == timeline_id))
    timeline = timeline_result.scalar_one_or_none()
    if not timeline or timeline.status != "sealed":
        return None
        
    witness_result = await db.execute(select(CommercialWitness).where(CommercialWitness.id == witness_id))
    witness = witness_result.scalar_one_or_none()
    if not witness or witness.status != "active":
        return None

    root = timeline.merkle_root
    is_prod = get_settings().app_env == "production"
    
    if is_prod:
        from app.services.inference.cryptographic_receipts import sign_payload
        # Real cryptographic signature of root and witness ID
        payload = f"{root}:{witness.id}"
        signature = sign_payload(payload)
    else:
        # Simulate signature for development/test
        payload = f"{root}:{witness.id}:{get_settings().admin_token}"
        signature = hashlib.sha256(payload.encode()).hexdigest()
    
    sig = CommercialWitnessSignature(
        timeline_id=timeline_id,
        witness_id=witness_id,
        merkle_root=root,
        signature=signature,
        signature_algorithm=get_settings().commercial_witness_signature_algorithm,
        verification_status="valid"
    )
    db.add(sig)
    await db.commit()
    await db.refresh(sig)
    
    # Verify signature immediately before storing or completing
    is_valid = await verify_witness_signature(db, sig.id)
    if not is_valid:
        sig.verification_status = "invalid"
        await db.commit()
        return None
    
    await record_witness_audit_event(
        db,
        event_type="signature_received",
        witness_id=witness_id,
        timeline_id=timeline_id,
        summary=f"Signature for timeline {timeline_id} received from {witness.witness_name}"
    )
    return sig

async def verify_witness_signature(
    db: AsyncSession,
    signature_id: uuid.UUID
) -> bool:
    sig_result = await db.execute(
        select(CommercialWitnessSignature).where(CommercialWitnessSignature.id == signature_id)
    )
    sig = sig_result.scalar_one_or_none()
    if not sig or not sig.signature:
        return False
        
    witness_result = await db.execute(select(CommercialWitness).where(CommercialWitness.id == sig.witness_id))
    witness = witness_result.scalar_one_or_none()
    if not witness:
        return False
        
    timeline_result = await db.execute(select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.id == sig.timeline_id))
    timeline = timeline_result.scalar_one_or_none()
    if not timeline:
        return False

    is_prod = get_settings().app_env == "production"
    sig_str = sig.signature.lower()
    if is_prod:
        if any(p in sig_str for p in ["placeholder", "mock", "stub", "simulated", "fake"]):
            sig.verification_status = "invalid"
            await db.commit()
            return False
            
    # Verification logic: try real Ed25519 first, fallback to mock if not in prod
    from app.services.inference.cryptographic_receipts import verify_payload_signature
    real_payload = f"{timeline.merkle_root}:{witness.id}"
    
    is_valid = verify_payload_signature(real_payload, sig.signature)
    if not is_valid and not is_prod:
        # Fallback to simulated signature in non-production
        mock_payload = f"{timeline.merkle_root}:{witness.id}:{get_settings().admin_token}"
        expected = hashlib.sha256(mock_payload.encode()).hexdigest()
        is_valid = sig.signature == expected
        
    if not is_valid:
        sig.verification_status = "invalid"
    else:
        sig.verification_status = "valid"
        
    await db.commit()
    return is_valid

async def evaluate_witness_quorum(
    db: AsyncSession,
    timeline_id: uuid.UUID
) -> dict:
    # 1. Get timeline
    timeline_result = await db.execute(select(CommercialMerkleTimeline).where(CommercialMerkleTimeline.id == timeline_id))
    timeline = timeline_result.scalar_one_or_none()
    if not timeline:
        return {"status": "error", "message": "Timeline not found"}
        
    # 2. Get policy
    policy_result = await db.execute(
        select(CommercialWitnessQuorumPolicy).where(
            CommercialWitnessQuorumPolicy.timeline_type == timeline.timeline_type,
            CommercialWitnessQuorumPolicy.enabled == True
        )
    )
    policy = policy_result.scalar_one_or_none()
    
    # Fallback to defaults if no policy
    req_sigs = policy.required_signatures if policy else get_settings().commercial_witness_min_signatures
    req_ext = policy.require_external_witness if policy else get_settings().commercial_witness_require_external
    
    # 3. Get valid signatures
    sigs_result = await db.execute(
        select(CommercialWitnessSignature).where(
            CommercialWitnessSignature.timeline_id == timeline_id,
            CommercialWitnessSignature.verification_status == "valid"
        )
    )
    sigs = sigs_result.scalars().all()
    
    valid_count = len(sigs)
    has_external = False
    
    for s in sigs:
        w_result = await db.execute(select(CommercialWitness).where(CommercialWitness.id == s.witness_id))
        w = w_result.scalar_one_or_none()
        if w and w.witness_type == "external":
            has_external = True
            
    meets_quorum = valid_count >= req_sigs
    if req_ext and not has_external:
        meets_quorum = False
        
    status = "met" if meets_quorum else "failed"
    
    return {
        "timeline_id": str(timeline_id),
        "quorum_status": status,
        "signatures_found": valid_count,
        "signatures_required": req_sigs,
        "external_witness_present": has_external,
        "external_witness_required": req_ext,
        "signatures": [
            {
                "witness_id": str(s.witness_id),
                "signature": s.signature,
                "signed_at": s.signed_at.isoformat() if s.signed_at else None
            }
            for s in sigs
        ],
        "verified_at": datetime.now(UTC).isoformat()
    }

async def summarize_witness_status(db: AsyncSession) -> dict:
    witnesses_result = await db.execute(select(CommercialWitness))
    witnesses = witnesses_result.scalars().all()
    
    status_summary = {
        "total_witnesses": len(witnesses),
        "active": 0,
        "disabled": 0,
        "offline": 0,
        "untrusted": 0,
        "types": {}
    }
    
    for w in witnesses:
        status_summary[w.status] += 1
        w_type = w.witness_type
        status_summary["types"][w_type] = status_summary["types"].get(w_type, 0) + 1
        
    return status_summary

async def record_witness_audit_event(
    db: AsyncSession,
    event_type: str,
    witness_id: Optional[uuid.UUID] = None,
    timeline_id: Optional[uuid.UUID] = None,
    summary: str = ""
) -> CommercialWitnessAuditEvent:
    # Use a fixed ISO string for consistent datetime parsing and validation
    now_str = datetime.now(UTC).isoformat()
    payload = f"{event_type}:{witness_id}:{timeline_id}:{summary}:{now_str}"
    
    is_prod = get_settings().app_env == "production"
    if is_prod:
        from app.services.inference.cryptographic_receipts import sign_payload
        immutable_hash = sign_payload(payload)
    else:
        immutable_hash = hashlib.sha256(payload.encode()).hexdigest()
    
    event = CommercialWitnessAuditEvent(
        event_type=event_type,
        witness_id=witness_id,
        timeline_id=timeline_id,
        summary=summary,
        immutable_hash=immutable_hash,
        created_at=datetime.fromisoformat(now_str)
    )
    db.add(event)
    await db.commit()
    return event

async def verify_witness_audit_event(
    db: AsyncSession,
    event_id: uuid.UUID
) -> bool:
    res = await db.execute(
        select(CommercialWitnessAuditEvent).where(CommercialWitnessAuditEvent.id == event_id)
    )
    event = res.scalar_one_or_none()
    if not event or not event.immutable_hash:
        return False
        
    created_at_str = event.created_at.isoformat() if event.created_at else ""
    payload = f"{event.event_type}:{event.witness_id}:{event.timeline_id}:{event.summary}:{created_at_str}"
    
    is_prod = get_settings().app_env == "production"
    
    from app.services.inference.cryptographic_receipts import verify_payload_signature
    is_valid = verify_payload_signature(payload, event.immutable_hash)
    
    if not is_valid and not is_prod:
        expected = hashlib.sha256(payload.encode()).hexdigest()
        is_valid = event.immutable_hash == expected
        
    return is_valid
