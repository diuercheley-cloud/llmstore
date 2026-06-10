import io
import pytest
from fastapi import UploadFile, HTTPException
from app.services.multimodal.vision_runtime import VisionRuntimeService
from app.services.multimodal.base import MultimodalInputType, MultimodalCapability


@pytest.fixture
def vision_service():
    return VisionRuntimeService()


@pytest.mark.asyncio
async def test_analyze_vision_valid_image(vision_service):
    # Mocking UploadFile
    content = b"fake image content"
    file = UploadFile(
        filename="test.jpg",
        file=io.BytesIO(content)
    )
    
    result = await vision_service.analyze_vision(file, prompt="What is this?", model_hint="llava")
    
    assert result.text is not None
    assert "Mock Llava" in result.text
    assert result.model_used == "llava-v1.5-7b"
    assert "file_hash" in result.audit_metadata
    assert result.audit_metadata["original_filename"] == "test.jpg"


@pytest.mark.asyncio
async def test_analyze_vision_invalid_extension(vision_service):
    file = UploadFile(
        filename="test.txt",
        file=io.BytesIO(b"not an image")
    )
    
    with pytest.raises(HTTPException) as excinfo:
        await vision_service.analyze_vision(file)
    
    assert excinfo.value.status_code == 400
    assert "Unsupported image type" in excinfo.value.detail


@pytest.mark.asyncio
async def test_analyze_video_valid(vision_service):
    content = b"fake video content"
    file = UploadFile(
        filename="test.mp4",
        file=io.BytesIO(content)
    )
    
    result = await vision_service.analyze_video(file, prompt="Summarize", model_hint="video-llama")
    
    assert result.text is not None
    assert "VideoLlama" in result.text
    assert result.model_used == "Video-LLaMA"
    assert "file_hash" in result.audit_metadata


@pytest.mark.asyncio
async def test_capabilities_listing(vision_service):
    caps = vision_service.get_capabilities()
    
    assert "llava" in caps
    assert "qwen-vl" in caps
    assert "ocr" in caps["qwen-vl"]
    assert "video_summary" in caps["video-llama"]


@pytest.mark.asyncio
async def test_adapter_fallback(vision_service):
    # If an unknown model hint is provided, it should fallback to llava
    content = b"fake image content"
    file = UploadFile(
        filename="test.jpg",
        file=io.BytesIO(content)
    )
    
    result = await vision_service.analyze_vision(file, model_hint="unknown-model")
    
    assert result.model_used == "llava-v1.5-7b" # Default fallback
