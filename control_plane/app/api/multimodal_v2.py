from typing import List, Optional

from app.api.deps import get_db_session
from app.services.multimodal.vision_runtime import VisionRuntimeService
from app.services.multimodal.base import MultimodalResult
from fastapi import APIRouter, Depends, File, Form, UploadFile, status

router = APIRouter(prefix="/api/multimodal", tags=["multimodal-v2"])


@router.post("/vision/analyze", status_code=status.HTTP_200_OK)
async def analyze_vision(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    model_hint: str = Form("llava"),
    service: VisionRuntimeService = Depends(VisionRuntimeService)
):
    """
    Analyzes an image using a multimodal vision model.
    """
    return await service.analyze_vision(file, prompt, model_hint)


@router.post("/video/analyze", status_code=status.HTTP_200_OK)
async def analyze_video(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    model_hint: str = Form("video-llama"),
    service: VisionRuntimeService = Depends(VisionRuntimeService)
):
    """
    Analyzes a video using a multimodal video model.
    """
    return await service.analyze_video(file, prompt, model_hint)


@router.get("/capabilities")
async def get_multimodal_capabilities(
    service: VisionRuntimeService = Depends(VisionRuntimeService)
):
    """
    Lists all available multimodal adapters and their capabilities.
    """
    return service.get_capabilities()
