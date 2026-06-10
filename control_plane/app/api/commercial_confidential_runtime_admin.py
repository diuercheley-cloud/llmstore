# Owner: commercial-ops
from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.dependencies import get_admin_user
from ..db.session import get_db
from ..models.commercial.commercial_confidential_runtime import (
    CommercialConfidentialInferenceSession,
    CommercialConfidentialRuntimeAuditEvent,
    CommercialConfidentialRuntimeProfile,
)
from ..services.inference import confidential_runtime

router = APIRouter(prefix="/admin/inference/confidential-runtime", tags=["Confidential Runtime Admin"])

@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    return await confidential_runtime.summarize_confidential_runtime(db)

@router.get("/profiles", response_model=List[dict])
async def list_profiles(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialConfidentialRuntimeProfile).order_by(CommercialConfidentialRuntimeProfile.created_at.desc()))
    profiles = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "profile_name": p.profile_name,
            "client_id": p.client_id,
            "enabled": p.enabled,
            "require_encrypted_input": p.require_encrypted_input,
            "prohibit_prompt_logging": p.prohibit_prompt_logging,
            "created_at": p.created_at.isoformat()
        }
        for p in profiles
    ]

@router.post("/profiles")
async def create_profile(payload: dict, db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    profile = CommercialConfidentialRuntimeProfile(
        profile_name=payload["profile_name"],
        client_id=payload.get("client_id"),
        enabled=payload.get("enabled", True),
        require_encrypted_input=payload.get("require_encrypted_input", False),
        require_encrypted_output=payload.get("require_encrypted_output", False),
        prohibit_prompt_logging=payload.get("prohibit_prompt_logging", True),
        prohibit_response_logging=payload.get("prohibit_response_logging", True),
        require_runtime_attestation=payload.get("require_runtime_attestation", False),
        require_model_trust=payload.get("require_model_trust", True),
        max_retention_seconds=payload.get("max_retention_seconds", 0)
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.get("/sessions", response_model=List[dict])
async def list_sessions(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialConfidentialInferenceSession).order_by(CommercialConfidentialInferenceSession.created_at.desc()).limit(100))
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "client_id": s.client_id,
            "request_id": s.request_id,
            "input_mode": s.input_mode,
            "attestation_status": s.attestation_status,
            "created_at": s.created_at.isoformat()
        }
        for s in sessions
    ]

@router.get("/audit", response_model=List[dict])
async def list_audit(db: AsyncSession = Depends(get_db), admin: Any = Depends(get_admin_user)):
    result = await db.execute(select(CommercialConfidentialRuntimeAuditEvent).order_by(CommercialConfidentialRuntimeAuditEvent.created_at.desc()).limit(100))
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "session_id": str(e.session_id) if e.session_id else None,
            "event_type": e.event_type,
            "summary": e.summary,
            "created_at": e.created_at.isoformat()
        }
        for e in events
    ]
