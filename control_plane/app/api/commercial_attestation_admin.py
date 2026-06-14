# Owner: commercial-ops
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.dependencies import get_admin_user
from app.services.runtime_dependencies import get_db
from ..models.commercial.commercial_attestation_runtime import (
    CommercialAttestationChallenge,
    CommercialAttestationEvidence,
    CommercialAttestationPolicy,
    CommercialRuntimeAttestation,
)
from ..services.security import attestation_challenges as ac
from ..services.security import attestation_measurements as am
from ..services.security import runtime_attestation as ra
from ..services.security import runtime_integrity as ri

router = APIRouter(prefix="/admin/attestation", tags=["Attestation Runtime Admin"])


@router.get("/runtime")
async def list_runtime_attestations(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
    cluster_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    query = select(CommercialRuntimeAttestation)
    if cluster_id:
        query = query.where(CommercialRuntimeAttestation.cluster_id == cluster_id)
    if status:
        query = query.where(CommercialRuntimeAttestation.status == status)
    query = query.order_by(CommercialRuntimeAttestation.created_at.desc()).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "node_id": item.node_id,
            "cluster_id": item.cluster_id,
            "status": item.status,
            "trusted": item.trusted,
            "trust_score": item.trust_score,
            "drift_detected": item.drift_detected,
            "drift_score": item.drift_score,
            "attestation_mode": item.attestation_mode,
            "enclave_type": item.enclave_type,
            "platform_type": item.platform_type,
            "attested_at": item.attested_at.isoformat(),
            "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        }
        for item in items
    ]


@router.get("/runtime/summary")
async def get_runtime_summary(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    return await ra.summarize_attestation_status(db)


@router.post("/runtime")
async def create_runtime_attestation(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    return await ra.create_runtime_attestation(
        db,
        cluster_id=payload.get("cluster_id", "unknown"),
        node_id=payload.get("node_id"),
        tenant_id=payload.get("tenant_id"),
        runtime_hash=payload.get("runtime_hash"),
        firmware_hash=payload.get("firmware_hash"),
        model_hash=payload.get("model_hash"),
        workflow_hash=payload.get("workflow_hash"),
        policy_hash=payload.get("policy_hash"),
        enclave_type=payload.get("enclave_type"),
        platform_type=payload.get("platform_type"),
    )


@router.get("/runtime/{attestation_id}")
async def get_runtime_attestation(
    attestation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    record = await db.get(CommercialRuntimeAttestation, attestation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attestation not found")
    return {
        "id": str(record.id),
        "node_id": record.node_id,
        "cluster_id": record.cluster_id,
        "tenant_id": record.tenant_id,
        "runtime_hash": record.runtime_hash,
        "firmware_hash": record.firmware_hash,
        "model_hash": record.model_hash,
        "workflow_hash": record.workflow_hash,
        "policy_hash": record.policy_hash,
        "evidence_hash": record.evidence_hash,
        "measurement_chain_hash": record.measurement_chain_hash,
        "trust_score": record.trust_score,
        "attestation_mode": record.attestation_mode,
        "enclave_type": record.enclave_type,
        "platform_type": record.platform_type,
        "immutable_hash": record.immutable_hash,
        "previous_hash": record.previous_hash,
        "status": record.status,
        "trusted": record.trusted,
        "drift_detected": record.drift_detected,
        "drift_score": record.drift_score,
        "attested_at": record.attested_at.isoformat(),
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }


@router.post("/runtime/{attestation_id}/verify")
async def verify_runtime_attestation(
    attestation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    record = await ra.verify_runtime_attestation(db, attestation_id)
    return {
        "id": str(record.id),
        "status": record.status,
        "trusted": record.trusted,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
    }


@router.post("/runtime/{attestation_id}/drift")
async def detect_attestation_drift(
    attestation_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    return await ra.detect_drift(
        db,
        attestation_id,
        runtime_hash=payload.get("runtime_hash"),
        model_hash=payload.get("model_hash"),
        workflow_hash=payload.get("workflow_hash"),
    )


@router.post("/runtime/{attestation_id}/revoke")
async def revoke_attestation(
    attestation_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    record = await ra.revoke_attestation(db, attestation_id, reason=payload.get("reason"))
    return {
        "id": str(record.id),
        "status": record.status,
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
    }


@router.post("/runtime/{attestation_id}/trust-score")
async def compute_trust_score(
    attestation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    score = await ra.compute_trust_score(db, attestation_id)
    return {"attestation_id": str(attestation_id), "trust_score": score}


@router.get("/evidence")
async def list_evidence(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
    cluster_id: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    query = select(CommercialAttestationEvidence)
    if cluster_id:
        query = query.where(CommercialAttestationEvidence.cluster_id == cluster_id)
    query = query.order_by(CommercialAttestationEvidence.created_at.desc()).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "runtime_attestation_id": str(item.runtime_attestation_id) if item.runtime_attestation_id else None,
            "evidence_type": item.evidence_type,
            "evidence_hash": item.evidence_hash,
            "chain_position": item.chain_position,
            "enclave_type": item.enclave_type,
            "status": item.status,
            "verified": item.verified,
            "collected_at": item.collected_at.isoformat(),
        }
        for item in items
    ]


@router.get("/challenges")
async def list_challenges(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    query = select(CommercialAttestationChallenge)
    if status:
        query = query.where(CommercialAttestationChallenge.status == status)
    query = query.order_by(CommercialAttestationChallenge.created_at.desc()).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "challenge_type": item.challenge_type,
            "status": item.status,
            "response_received": item.response_received,
            "response_valid": item.response_valid,
            "verification_result": item.verification_result,
            "issued_at": item.issued_at.isoformat(),
            "responded_at": item.responded_at.isoformat() if item.responded_at else None,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        }
        for item in items
    ]


@router.post("/challenges")
async def issue_challenge(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    challenge = await ac.issue_challenge(
        db,
        cluster_id=payload.get("cluster_id", "unknown"),
        node_id=payload.get("node_id"),
        tenant_id=payload.get("tenant_id"),
        challenge_type=payload.get("challenge_type", "runtime_measurement"),
        required_measurements=payload.get("required_measurements"),
        trust_score_required=payload.get("trust_score_required", 0.0),
    )
    return {
        "id": str(challenge.id),
        "challenge_nonce": challenge.challenge_nonce,
        "challenge_type": challenge.challenge_type,
        "status": challenge.status,
        "issued_at": challenge.issued_at.isoformat(),
        "expires_at": challenge.expires_at.isoformat(),
    }


@router.post("/challenges/{challenge_id}/respond")
async def respond_to_challenge(
    challenge_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    challenge = await ac.respond_to_challenge(
        db,
        challenge_id,
        payload.get("response_data", {}),
        attestation_id=payload.get("attestation_id"),
    )
    return {
        "id": str(challenge.id),
        "status": challenge.status,
        "response_valid": challenge.response_valid,
        "verification_result": challenge.verification_result,
    }


@router.get("/verify")
async def verify_attestation_status(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    return await ra.summarize_attestation_status(db)


@router.get("/drift")
async def list_drift_events(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
    limit: int = Query(50, le=200),
):
    query = (
        select(CommercialRuntimeAttestation)
        .where(CommercialRuntimeAttestation.drift_detected.is_(True))
        .order_by(CommercialRuntimeAttestation.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "node_id": item.node_id,
            "cluster_id": item.cluster_id,
            "status": item.status,
            "drift_score": item.drift_score,
            "trust_score": item.trust_score,
            "drift_detected": item.drift_detected,
            "attested_at": item.attested_at.isoformat(),
        }
        for item in items
    ]


@router.get("/policies")
async def list_policies(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
    limit: int = Query(50, le=200),
):
    query = (
        select(CommercialAttestationPolicy)
        .order_by(CommercialAttestationPolicy.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": str(item.id),
            "policy_name": item.policy_name,
            "policy_hash": item.policy_hash,
            "policy_version": item.policy_version,
            "min_trust_score": item.min_trust_score,
            "max_drift_threshold": item.max_drift_threshold,
            "enforcement_mode": item.enforcement_mode,
            "block_untrusted": item.block_untrusted,
            "is_active": item.is_active,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


@router.post("/policies")
async def create_policy(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    policy = await ri.create_attestation_policy(
        db,
        policy_name=payload.get("policy_name", "default"),
        policy_version=payload.get("policy_version", "1.0"),
        min_trust_score=payload.get("min_trust_score", 0.0),
        max_drift_threshold=payload.get("max_drift_threshold", 0.1),
        require_signed_evidence=payload.get("require_signed_evidence", False),
        require_measurement_chain=payload.get("require_measurement_chain", False),
        require_model_binding=payload.get("require_model_binding", False),
        require_workflow_binding=payload.get("require_workflow_binding", False),
        allowed_enclave_types=payload.get("allowed_enclave_types"),
        allowed_platform_types=payload.get("allowed_platform_types"),
        enforcement_mode=payload.get("enforcement_mode", "report_only"),
        block_untrusted=payload.get("block_untrusted", False),
        require_for_sovereign=payload.get("require_for_sovereign", False),
        require_for_sensitive_tenants=payload.get("require_for_sensitive_tenants", False),
    )
    return {
        "id": str(policy.id),
        "policy_name": policy.policy_name,
        "policy_hash": policy.policy_hash,
        "is_active": policy.is_active,
    }


@router.get("/measurements")
async def list_measurements(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
    measurement_type: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    return await am.get_measurement_history(
        db,
        measurement_type=measurement_type,
        limit=limit,
    )


@router.get("/measurements/summary")
async def get_measurement_summary(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    return await am.summarize_measurements(db)


portal_router = APIRouter(prefix="/portal/attestation", tags=["Attestation Portal"])


@portal_router.get("/status")
async def get_portal_attestation_status(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_admin_user),
):
    return await ra.summarize_attestation_status(db)
