import base64
import hashlib
import logging
import os
import uuid
from urllib.parse import urlparse

import httpx
from app.core.config import get_settings
from app.models.multimodal import MultimodalAsset
from app.services.multimodal.multimodal_policy import MultimodalPolicyService
from app.services.multimodal.multimodal_usage import MultimodalUsageService
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

try:
    import io

    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class VisionService:
    @property
    def settings(self):
        return get_settings()

    def __init__(self):
        self.policy_service = MultimodalPolicyService()
        self.usage_service = MultimodalUsageService()
        
        # Ensure storage directory exists
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.storage_dir = os.path.join(base_dir, "data", "multimodal_assets")
        os.makedirs(self.storage_dir, exist_ok=True)

    def _validate_internal_url(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        # Accept localhost, 127.0.0.1, internal IP ranges, or domains ending with local/internal
        is_internal = (
            hostname in ("localhost", "127.0.0.1", "internal") or
            hostname.startswith("10.") or
            hostname.startswith("192.168.") or
            hostname.startswith("172.16.") or
            hostname.endswith(".local") or
            hostname.endswith(".internal")
        )
        if not is_internal:
            raise HTTPException(
                status_code=400,
                detail="External URLs are blocked by default for security."
            )

    def _sanitize_exif(self, image_bytes: bytes) -> tuple[bytes, bool]:
        if not HAS_PIL:
            logger.warning(
                "Pillow is not installed. EXIF sanitization skipped "
                "(bytes preserved)."
            )
            return image_bytes, False
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            output = io.BytesIO()
            # PIL save strips EXIF by default
            image.save(output, format=image.format or "JPEG")
            return output.getvalue(), True
        except Exception as e:
            logger.error(f"Error sanitizing EXIF: {e}")
            return image_bytes, False

    async def process_image(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        image_upload: UploadFile = None,
        base64_data: str = None,
        image_url: str = None,
        run_ocr: bool = False
    ) -> dict:
        # 1. Policy check
        await self.policy_service.check_policy(db, client_id, "vision", input_text=image_url)

        image_bytes = b""
        mime_type = "image/jpeg"
        filename = "image.jpg"

        # 2. Extract image bytes based on input type
        if image_upload:
            image_bytes = await image_upload.read()
            mime_type = image_upload.content_type or "image/jpeg"
            filename = image_upload.filename or "image.jpg"
        elif base64_data:
            # Handle possible base64 headers
            if "," in base64_data:
                header, base64_data = base64_data.split(",", 1)
                if "image/png" in header:
                    mime_type = "image/png"
                    filename = "image.png"
            image_bytes = base64.b64decode(base64_data)
        elif image_url:
            self._validate_internal_url(image_url)
            async with httpx.AsyncClient() as client:
                try:
                    res = await client.get(image_url, timeout=10)
                    res.raise_for_status()
                    image_bytes = res.content
                    mime_type = res.headers.get("content-type", "image/jpeg")
                    parsed_path = urlparse(image_url).path
                    filename = os.path.basename(parsed_path) or "image.jpg"
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to fetch image from URL: {str(e)}"
                    )
        else:
            raise HTTPException(
                status_code=400,
                detail="No image input provided. Must specify upload, base64_data, or image_url."
            )

        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty image bytes provided.")

        # 3. Sanitise EXIF
        bytes_sanitized, sanitized = self._sanitize_exif(image_bytes)

        # 4. Compute file hash
        file_hash = hashlib.sha256(bytes_sanitized).hexdigest()

        # 5. Save file to storage
        asset_id = uuid.uuid4()
        ext = os.path.splitext(filename)[1] or ".jpg"
        storage_path = os.path.join(self.storage_dir, f"{asset_id}{ext}")
        with open(storage_path, "wb") as f:
            f.write(bytes_sanitized)

        # 6. Create Asset record
        asset = MultimodalAsset(
            id=asset_id,
            client_id=client_id,
            asset_type="image",
            storage_path=storage_path,
            file_size_bytes=len(bytes_sanitized),
            mime_type=mime_type,
            file_hash=file_hash,
            provenance="uploaded",
            exif_sanitized=sanitized,
            metadata_json={"original_filename": filename}
        )
        db.add(asset)
        await db.commit()

        # 7. Log request and usage
        req = await self.usage_service.log_request(
            db, client_id, "vision", "completed", input_asset_id=asset_id
        )
        await self.usage_service.record_usage(
            db, client_id, req.id, "vision", unit_count=1
        )

        # 8. Mock description, OCR, classification and visual analysis
        description = "A clean mock representation of the processed image."
        ocr_result = None
        if run_ocr:
            ocr_result = (
                "MOCK OCR TEXT: Hello from llm-inference-stack "
                "multimodal platform."
            )
        
        return {
            "asset_id": str(asset_id),
            "description": description,
            "ocr": ocr_result,
            "classification": ["mock-object", "scenery"],
            "visual_analysis": {
                "dominant_colors": ["#FFFFFF", "#000000"],
                "aspect_ratio": "1.0",
                "objects_detected": ["mock_bounding_box_1", "mock_bounding_box_2"]
            }
        }
