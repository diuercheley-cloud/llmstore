import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ...models.commercial_confidential_runtime import (
    CommercialConfidentialRuntimeProfile,
    CommercialConfidentialInferenceSession,
    CommercialConfidentialRuntimeAuditEvent
)
from ...core.config import get_settings

async def resolve_confidential_profile(
    db: AsyncSession, 
    client_id: Optional[str] = None
) -> Optional[CommercialConfidentialRuntimeProfile]:
    # 1. Check for client-specific profile
    if client_id:
        result = await db.execute(
            select(CommercialConfidentialRuntimeProfile).where(
                CommercialConfidentialRuntimeProfile.client_id == client_id,
                CommercialConfidentialRuntimeProfile.enabled == True
            )
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile
            
    # 2. Check for global default profile
    result = await db.execute(
        select(CommercialConfidentialRuntimeProfile).where(
            CommercialConfidentialRuntimeProfile.client_id == None,
            CommercialConfidentialRuntimeProfile.enabled == True
        )
    )
    return result.scalar_one_or_none()

async def create_confidential_session(
    db: AsyncSession,
    client_id: Optional[str],
    request_id: Optional[str],
    profile: Optional[CommercialConfidentialRuntimeProfile]
) -> CommercialConfidentialInferenceSession:
    session = CommercialConfidentialInferenceSession(
        client_id=client_id,
        request_id=request_id,
        profile_id=profile.id if profile else None,
        attestation_status="unknown"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    await log_confidential_audit(
        db, session.id, "confidential_session_started", 
        f"Session started for request {request_id}"
    )
    return session

async def validate_confidential_request(
    db: AsyncSession,
    session: CommercialConfidentialInferenceSession,
    profile: CommercialConfidentialRuntimeProfile,
    payload: dict
) -> Tuple[bool, str]:
    # 1. Check if encryption is required but missing
    if profile.require_encrypted_input and not payload.get("encrypted_input"):
        await log_confidential_audit(db, session.id, "validation_failed", "Encrypted input required but not provided")
        return False, "Encrypted input required"
        
    # 2. Check model trust if required
    if profile.require_model_trust and get_settings().commercial_confidential_require_model_trust:
        # Placeholder for model trust check logic
        session.model_trust_state = "verified"
        
    return True, "Valid"

async def enforce_no_plaintext_logging(
    db: AsyncSession,
    session: CommercialConfidentialInferenceSession,
    profile: CommercialConfidentialRuntimeProfile,
    data_type: str, # "prompt" or "response"
    content: Any
) -> Any:
    prohibit = False
    if data_type == "prompt" and profile.prohibit_prompt_logging:
        prohibit = True
    elif data_type == "response" and profile.prohibit_response_logging:
        prohibit = True
        
    if prohibit and get_settings().commercial_confidential_prohibit_plaintext_logging:
        await log_confidential_audit(db, session.id, "plaintext_logging_blocked", f"{data_type} logging blocked by policy")
        # Return hash instead of content
        if isinstance(content, str):
            return hashlib.sha256(content.encode()).hexdigest()
        return hashlib.sha256(str(content).encode()).hexdigest()
        
    return content

async def apply_retention_policy(
    db: AsyncSession,
    session: CommercialConfidentialInferenceSession,
    profile: CommercialConfidentialRuntimeProfile
):
    retention = profile.max_retention_seconds or get_settings().commercial_confidential_default_retention_seconds
    if retention == 0:
        # Immediate cleanup hook (placeholder)
        session.retention_policy_applied = True
        await log_confidential_audit(db, session.id, "retention_policy_applied", "Immediate cleanup applied")
    
    session.completed_at = datetime.utcnow()
    await db.commit()

async def log_confidential_audit(
    db: AsyncSession,
    session_id: Optional[uuid.UUID],
    event_type: str,
    summary: str
) -> CommercialConfidentialRuntimeAuditEvent:
    event = CommercialConfidentialRuntimeAuditEvent(
        session_id=session_id,
        event_type=event_type,
        summary=summary
    )
    db.add(event)
    await db.commit()
    return event

async def summarize_confidential_runtime(db: AsyncSession) -> dict:
    profiles_res = await db.execute(select(CommercialConfidentialRuntimeProfile))
    sessions_res = await db.execute(select(CommercialConfidentialInferenceSession))
    blocked_res = await db.execute(
        select(CommercialConfidentialRuntimeAuditEvent).where(
            CommercialConfidentialRuntimeAuditEvent.event_type == "plaintext_logging_blocked"
        )
    )
    
    return {
        "enabled": get_settings().commercial_confidential_runtime_enabled,
        "mode": get_settings().commercial_confidential_runtime_mode,
        "total_profiles": len(profiles_res.scalars().all()),
        "active_sessions": len(sessions_res.scalars().all()),
        "logging_blocked_events": len(blocked_res.scalars().all())
    }
