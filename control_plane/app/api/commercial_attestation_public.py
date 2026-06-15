# Owner: commercial-ops
import hashlib
import json

from app.services.runtime_dependencies import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..services.inference import public_attestation_gateway

router = APIRouter(prefix="/attestation", tags=["Public Attestation"])


def check_gateway_enabled():
    if not get_settings().commercial_public_attestation_gateway_enabled:
        raise HTTPException(status_code=503, detail="Public Attestation Gateway is disabled")


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    check_gateway_enabled()
    return await public_attestation_gateway.summarize_gateway_status(db)


@router.post("/verify/receipt")
async def verify_receipt(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(None),
):
    check_gateway_enabled()

    receipt_hash = payload.get("receipt_hash")
    if not receipt_hash:
        raise HTTPException(status_code=400, detail="Missing receipt_hash")

    # Log request
    req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    att_req = await public_attestation_gateway.log_attestation_request(
        db, req_hash, source_ip=request.client.host, user_agent=user_agent
    )

    result = await public_attestation_gateway.verify_public_receipt(db, receipt_hash)

    # Store result
    att_res = public_attestation_gateway.CommercialPublicAttestationResult(
        request_id=att_req.id,
        verification_type="receipt",
        result=result["status"],
        result_json=result,
    )
    db.add(att_res)

    att_req.status = "verified" if result["status"] == "valid" else "invalid"
    await db.commit()

    return result


@router.post("/verify/timeline")
async def verify_timeline(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(None),
):
    check_gateway_enabled()

    root = payload.get("merkle_root")
    if not root:
        raise HTTPException(status_code=400, detail="Missing merkle_root")

    req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    att_req = await public_attestation_gateway.log_attestation_request(
        db, req_hash, source_ip=request.client.host, user_agent=user_agent
    )

    result = await public_attestation_gateway.verify_public_timeline(db, root)

    att_res = public_attestation_gateway.CommercialPublicAttestationResult(
        request_id=att_req.id,
        verification_type="timeline",
        result=result["status"],
        result_json=result,
    )
    db.add(att_res)
    await db.commit()

    return result


@router.post("/verify/witness-quorum")
async def verify_witness_quorum(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(None),
):
    check_gateway_enabled()

    root = payload.get("merkle_root")
    if not root:
        raise HTTPException(status_code=400, detail="Missing merkle_root")

    req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    att_req = await public_attestation_gateway.log_attestation_request(
        db, req_hash, source_ip=request.client.host, user_agent=user_agent
    )

    result = await public_attestation_gateway.verify_public_witness_quorum(db, root)

    att_res = public_attestation_gateway.CommercialPublicAttestationResult(
        request_id=att_req.id,
        verification_type="witness_quorum",
        result="valid" if result.get("quorum_status") == "met" else "invalid",
        result_json=result,
    )
    db.add(att_res)
    await db.commit()

    return result


@router.post("/verify/retrieval-proof")
async def verify_retrieval_proof(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(None),
):
    check_gateway_enabled()
    proof_hash = payload.get("proof_hash")
    if not proof_hash:
        raise HTTPException(status_code=400, detail="Missing proof_hash")
    req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    att_req = await public_attestation_gateway.log_attestation_request(
        db, req_hash, proof_hash=proof_hash, source_ip=request.client.host, user_agent=user_agent
    )
    result = await public_attestation_gateway.verify_public_retrieval_proof(db, proof_hash)
    att_res = public_attestation_gateway.CommercialPublicAttestationResult(
        request_id=att_req.id,
        verification_type="retrieval_proof",
        result=result["status"],
        result_json=result,
    )
    db.add(att_res)
    await db.commit()
    return result


@router.post("/verify/lineage-consistency")
async def verify_lineage_consistency(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(None),
):
    check_gateway_enabled()
    proof_hash = payload.get("proof_hash")
    if not proof_hash:
        raise HTTPException(status_code=400, detail="Missing proof_hash")
    req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    att_req = await public_attestation_gateway.log_attestation_request(
        db, req_hash, proof_hash=proof_hash, source_ip=request.client.host, user_agent=user_agent
    )
    result = await public_attestation_gateway.verify_public_lineage_consistency(db, proof_hash)
    att_res = public_attestation_gateway.CommercialPublicAttestationResult(
        request_id=att_req.id,
        verification_type="lineage_consistency",
        result=result["status"],
        result_json=result,
    )
    db.add(att_res)
    await db.commit()
    return result


@router.post("/verify/retrieval-replay")
async def verify_retrieval_replay(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_agent: str | None = Header(None),
):
    check_gateway_enabled()
    proof_hash = payload.get("proof_hash")
    if not proof_hash:
        raise HTTPException(status_code=400, detail="Missing proof_hash")
    req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    att_req = await public_attestation_gateway.log_attestation_request(
        db, req_hash, proof_hash=proof_hash, source_ip=request.client.host, user_agent=user_agent
    )
    result = await public_attestation_gateway.verify_public_retrieval_replay(db, proof_hash)
    att_res = public_attestation_gateway.CommercialPublicAttestationResult(
        request_id=att_req.id,
        verification_type="retrieval_replay",
        result=result["status"],
        result_json=result,
    )
    db.add(att_res)
    await db.commit()
    return result
