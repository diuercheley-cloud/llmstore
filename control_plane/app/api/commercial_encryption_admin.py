import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import get_settings
from app.models.commercial_encryption import (
    CommercialTenantEncryptionKey,
    CommercialEncryptedArtifact,
    CommercialEncryptionAuditEvent,
)
from app.schemas.commercial_encryption import (
    EncryptionKeyResponse,
    EncryptionKeyCreate,
    EncryptRequest,
    EncryptedArtifactResponse,
    DecryptRequest,
    DecryptResponse,
    AuditEventResponse,
    ClassificationRequest,
    ClassificationResponse,
)
from app.services.security.tenant_encryption import TenantEncryptionService
from app.services.auth import AdminRole

router = APIRouter()
settings = get_settings()

def get_encryption_service():
    return TenantEncryptionService(settings)

@router.get("/keys", response_model=List[EncryptionKeyResponse])
async def list_encryption_keys(
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.READ)),
    client_id: Optional[uuid.UUID] = None,
):
    stmt = select(CommercialTenantEncryptionKey)
    if client_id:
        stmt = stmt.where(CommercialTenantEncryptionKey.client_id == client_id)
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/keys", response_model=EncryptionKeyResponse)
async def create_encryption_key(
    request: EncryptionKeyCreate,
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.SUPER)),
    service: TenantEncryptionService = Depends(get_encryption_service),
):
    return await service.create_tenant_key(db, request.client_id, request.purpose)

@router.post("/keys/{key_id}/rotate", response_model=EncryptionKeyResponse)
async def rotate_encryption_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.SUPER)),
    service: TenantEncryptionService = Depends(get_encryption_service),
):
    return await service.rotate_tenant_key(db, key_id)

@router.post("/keys/{key_id}/revoke")
async def revoke_encryption_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.SUPER)),
    service: TenantEncryptionService = Depends(get_encryption_service),
):
    await service.revoke_tenant_key(db, key_id)
    return {"status": "revoked"}

@router.post("/encrypt", response_model=EncryptedArtifactResponse)
async def encrypt_payload(
    request: EncryptRequest,
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.WRITE)),
    service: TenantEncryptionService = Depends(get_encryption_service),
):
    return await service.encrypt_payload(
        db,
        request.client_id,
        request.payload,
        request.artifact_type,
        request.resource_type,
        request.resource_id,
        request.key_purpose,
    )

@router.post("/decrypt", response_model=DecryptResponse)
async def decrypt_payload(
    request: DecryptRequest,
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.WRITE)),
    service: TenantEncryptionService = Depends(get_encryption_service),
):
    artifact = await db.get(CommercialEncryptedArtifact, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    try:
        payload = await service.decrypt_payload(db, artifact)
        return DecryptResponse(payload=payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/audit", response_model=List[AuditEventResponse])
async def list_encryption_audit(
    db: AsyncSession = Depends(deps.get_db),
    _role: AdminRole = Depends(deps.require_admin_role(AdminRole.READ)),
    client_id: Optional[uuid.UUID] = None,
):
    stmt = select(CommercialEncryptionAuditEvent)
    if client_id:
        stmt = stmt.where(CommercialEncryptionAuditEvent.client_id == client_id)
    stmt = stmt.order_by(CommercialEncryptionAuditEvent.created_at.desc()).limit(100)
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/classification", response_model=ClassificationResponse)
async def classify_payload(
    request: ClassificationRequest,
    service: TenantEncryptionService = Depends(get_encryption_service),
):
    classification = await service.classify_sensitive_payload(request.payload)
    return ClassificationResponse(classification=classification)
