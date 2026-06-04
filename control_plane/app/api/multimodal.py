import uuid

from app.api.dependencies import get_current_client, get_db
from app.models.client import Client
from app.services.multimodal.asset_store import AssetStore
from app.services.multimodal.speech_to_text_service import SpeechToTextService
from app.services.multimodal.vision_service import VisionService
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v1/multimodal", tags=["multimodal"])


class VisionRequest(BaseModel):
    asset_id: uuid.UUID
    do_ocr: bool = False
    tenant_id: str = "default"


class SpeechRequest(BaseModel):
    asset_id: uuid.UUID
    tenant_id: str = "default"


@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    tenant_id: str = Form("default"),
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client)
):
    """Uploads a multimodal asset, sanitizes it, and returns the asset details."""
    resolved_tenant = request.headers.get("x-tenant-id") or tenant_id or "default"
    file_bytes = await file.read()
    
    store = AssetStore(db)
    asset = await store.store_asset(
        client_id=client.id,
        tenant_id=resolved_tenant,
        asset_type=asset_type,
        file_bytes=file_bytes,
        mime_type=file.content_type or "application/octet-stream"
    )
    
    return {
        "id": asset.id,
        "tenant_id": asset.tenant_id,
        "asset_type": asset.asset_type,
        "file_hash": asset.file_hash,
        "mime_type": asset.mime_type,
        "size": asset.file_size_bytes,
        "redaction_status": asset.redaction_status,
        "created_at": asset.created_at.isoformat()
    }


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: uuid.UUID,
    request: Request,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client)
):
    """Retrieves metadata of a specific asset, verifying tenant isolation."""
    resolved_tenant = request.headers.get("x-tenant-id") or tenant_id or "default"
    store = AssetStore(db)
    asset = await store.get_asset(asset_id, resolved_tenant)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
        
    return {
        "id": asset.id,
        "tenant_id": asset.tenant_id,
        "asset_type": asset.asset_type,
        "file_hash": asset.file_hash,
        "mime_type": asset.mime_type,
        "size": asset.file_size_bytes,
        "redaction_status": asset.redaction_status,
        "created_at": asset.created_at.isoformat()
    }


@router.post("/vision")
async def analyze_vision(
    body: VisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client)
):
    """Performs image vision analysis."""
    resolved_tenant = request.headers.get("x-tenant-id") or body.tenant_id or "default"
    service = VisionService(db)
    result = await service.analyze_image(
        client_id=client.id,
        tenant_id=resolved_tenant,
        asset_id=body.asset_id,
        do_ocr=body.do_ocr
    )
    return result


@router.post("/speech-to-text")
async def speech_to_text(
    body: SpeechRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client)
):
    """Transcribes audio assets."""
    resolved_tenant = request.headers.get("x-tenant-id") or body.tenant_id or "default"
    service = SpeechToTextService(db)
    result = await service.transcribe_audio(
        client_id=client.id,
        tenant_id=resolved_tenant,
        asset_id=body.asset_id
    )
    return result
