import hashlib
import logging
import os
import uuid

from app.core.config import get_settings
from app.services.multimodal.adapters.florence2_adapter import Florence2Adapter
from app.services.multimodal.adapters.llava_adapter import LlavaAdapter
from app.services.multimodal.adapters.moondream_adapter import MoondreamAdapter
from app.services.multimodal.adapters.qwen_vl_adapter import QwenVLAdapter
from app.services.multimodal.adapters.video_llama_adapter import VideoLlamaAdapter
from app.services.multimodal.base import (
    MultimodalAdapterBase,
    MultimodalInputType,
    MultimodalResult,
)
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MAX_FILE_SIZE_MB = 20


class VisionRuntimeService:
    def __init__(self):
        self.settings = get_settings()
        self.adapters: dict[str, MultimodalAdapterBase] = {
            "llava": LlavaAdapter(),
            "qwen-vl": QwenVLAdapter(),
            "moondream": MoondreamAdapter(),
            "florence2": Florence2Adapter(),
            "video-llama": VideoLlamaAdapter(),
        }

    async def analyze_vision(
        self, file: UploadFile, prompt: str | None = None, model_hint: str = "llava"
    ) -> MultimodalResult:
        # 1. Validation
        await self._validate_file(file, MultimodalInputType.IMAGE)

        # 2. Hashing & Prep
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Temporary save for processing (simulated)
        temp_path = f"/tmp/{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        # In real world, we would write 'content' to temp_path

        # 3. Select Adapter
        adapter = self.adapters.get(model_hint, self.adapters["llava"])

        # 4. Run Analysis
        result = await adapter.analyze(
            input_type=MultimodalInputType.IMAGE, file_path=temp_path, prompt=prompt
        )

        # 5. Enrich with audit metadata
        if not result.audit_metadata:
            result.audit_metadata = {}
        result.audit_metadata.update(
            {
                "file_hash": file_hash,
                "original_filename": file.filename,
                "size_bytes": len(content),
                "timestamp": uuid.uuid1().time,
            }
        )

        return result

    async def analyze_video(
        self, file: UploadFile, prompt: str | None = None, model_hint: str = "video-llama"
    ) -> MultimodalResult:
        await self._validate_file(file, MultimodalInputType.VIDEO)

        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        adapter = self.adapters.get(model_hint, self.adapters["video-llama"])

        result = await adapter.analyze(
            input_type=MultimodalInputType.VIDEO,
            file_path=f"simulated://{file.filename}",
            prompt=prompt,
        )

        if not result.audit_metadata:
            result.audit_metadata = {}
        result.audit_metadata.update(
            {"file_hash": file_hash, "original_filename": file.filename, "size_bytes": len(content)}
        )

        return result

    def get_capabilities(self) -> dict[str, list[str]]:
        return {
            name: [cap.value for cap in adapter.capabilities]
            for name, adapter in self.adapters.items()
        }

    async def _validate_file(self, file: UploadFile, input_type: MultimodalInputType):
        ext = os.path.splitext(file.filename or "")[1].lower()

        if input_type == MultimodalInputType.IMAGE:
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported image type: {ext}")
        elif input_type == MultimodalInputType.VIDEO:
            if ext not in ALLOWED_VIDEO_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Unsupported video type: {ext}")

        # Size check
        # We need to seek to end to check size or use content-length if available
        # For simplicity, we'll assume it's checked or we read it
        pass
