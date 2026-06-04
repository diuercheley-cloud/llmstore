# Owner: commercial-ops
import uuid
from typing import Any, List

from app.api import deps
from app.models.commercial_crypto_trust import (
    CommercialKeyMaterial,
    CommercialKMSProvider,
    CryptoProviderType,
)
from app.services.security.key_rotation import KeyRotationService
from app.services.security.signing_service import SigningService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter()

# Schema placeholders for brevity
from pydantic import BaseModel


class ProviderCreate(BaseModel):
    name: str
    provider_type: CryptoProviderType
    config: dict = {}

class KeyCreate(BaseModel):
    provider_id: uuid.UUID
    key_alias: str
    key_type: str

class SignRequest(BaseModel):
    profile_id: uuid.UUID
    payload: str

class VerifyRequest(BaseModel):
    profile_id: uuid.UUID
    payload: str
    signature: str


@router.get("/providers", response_model=List[Any])
def get_providers(
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    providers = db.query(CommercialKMSProvider).all()
    return providers

@router.post("/providers", response_model=Any)
def create_provider(
    provider_in: ProviderCreate,
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    provider = CommercialKMSProvider(
        name=provider_in.name,
        provider_type=provider_in.provider_type,
        config=provider_in.config
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider

@router.get("/keys", response_model=List[Any])
def get_keys(
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    keys = db.query(CommercialKeyMaterial).all()
    return keys

@router.post("/keys", response_model=Any)
async def create_key(
    key_in: KeyCreate,
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    # This is a simplified creation process. 
    # Real implementations would trigger generation in the actual provider.
    from app.services.security.crypto_provider_registry import CryptoProviderRegistry
    
    provider_config = db.query(CommercialKMSProvider).filter(CommercialKMSProvider.id == key_in.provider_id).first()
    if not provider_config:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    provider = CryptoProviderRegistry.get_provider(provider_config.provider_type)
    key_data = await provider.generate_key(key_in.key_type)
    
    key = CommercialKeyMaterial(
        provider_id=key_in.provider_id,
        key_alias=key_in.key_alias,
        key_type=key_in.key_type,
        encrypted_key_blob=key_data.get("material")
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key

@router.post("/rotate", response_model=Any)
async def rotate_keys(
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    rotation_service = KeyRotationService(db)
    results = await rotation_service.process_rotations()
    return {"status": "completed", "details": results}

@router.post("/sign", response_model=Any)
async def sign_payload(
    req: SignRequest,
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    signing_service = SigningService(db)
    try:
        sig = await signing_service.sign_payload(req.profile_id, req.payload.encode('utf-8'))
        return {"signature": sig.decode('utf-8') if isinstance(sig, bytes) else sig}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify", response_model=Any)
async def verify_signature(
    req: VerifyRequest,
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    signing_service = SigningService(db)
    try:
        is_valid = await signing_service.verify_signature(
            req.profile_id, 
            req.payload.encode('utf-8'), 
            req.signature.encode('utf-8') if isinstance(req.signature, str) else req.signature
        )
        return {"valid": is_valid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trust-chain", response_model=Any)
def get_trust_chain(
    db: Session = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_active_superuser),
):
    # Return a mocked trust chain view for the dashboard
    return {
        "status": "ok",
        "nodes": [
            {"id": "root-ca", "type": "offline-root", "status": "active"},
            {"id": "intermediate-1", "type": "vault-hsm", "status": "active"},
            {"id": "leaf-tenant-a", "type": "local-keystore", "status": "active"}
        ],
        "links": [
            {"source": "root-ca", "target": "intermediate-1", "type": "signed_by"},
            {"source": "intermediate-1", "target": "leaf-tenant-a", "type": "signed_by"}
        ]
    }
