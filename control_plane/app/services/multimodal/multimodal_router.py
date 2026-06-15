import uuid

from app.db.session import get_db_session
from app.models.core.client import Client
from app.services.auth import require_admin, require_client
from app.services.multimodal.image_generation_service import ImageGenerationService
from app.services.multimodal.multimodal_policy import MultimodalPolicyService
from app.services.multimodal.multimodal_usage import MultimodalUsageService
from app.services.multimodal.speech_to_text_service import SpeechToTextService
from app.services.multimodal.vision_service import VisionService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["multimodal"])

vision_service = VisionService()
image_generation_service = ImageGenerationService()
speech_to_text_service = SpeechToTextService()
policy_service = MultimodalPolicyService()
usage_service = MultimodalUsageService()


class ImageGenRequest(BaseModel):
    prompt: str
    size: str | None = "1024x1024"
    provider: str | None = "mock"


@router.post("/v1/multimodal/vision")
async def post_vision(
    image_file: UploadFile | None = File(None),
    base64_data: str | None = Form(None),
    image_url: str | None = Form(None),
    run_ocr: bool | None = Form(False),
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await vision_service.process_image(
            db=db,
            client_id=client.id,
            image_upload=image_file,
            base64_data=base64_data,
            image_url=image_url,
            run_ocr=run_ocr,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/multimodal/image-generation")
async def post_image_generation(
    req: ImageGenRequest,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await image_generation_service.generate_image(
            db=db, client_id=client.id, prompt=req.prompt, size=req.size, provider=req.provider
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/multimodal/speech-to-text")
async def post_speech_to_text(
    audio_file: UploadFile | None = File(None),
    base64_audio: str | None = Form(None),
    save_audio: bool | None = Form(False),
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        result = await speech_to_text_service.transcribe_audio(
            db=db,
            client_id=client.id,
            audio_file=audio_file,
            base64_audio=base64_audio,
            save_audio_by_policy=save_audio,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/multimodal/assets/{asset_id}")
async def get_asset(
    asset_id: uuid.UUID,
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db_session),
):
    try:
        asset = await policy_service.check_asset_access(db, client.id, asset_id)
        return FileResponse(asset.storage_path, media_type=asset.mime_type)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/multimodal/usage")
async def get_admin_usage(admin=Depends(require_admin), db: AsyncSession = Depends(get_db_session)):
    try:
        result = await usage_service.get_usage_summary(db)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
