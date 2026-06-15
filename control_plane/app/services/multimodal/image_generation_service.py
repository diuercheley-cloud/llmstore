import base64
import hashlib
import logging
import os
import uuid

from app.core.config import get_settings
from app.models.core.multimodal import MultimodalAsset
from app.services.multimodal.multimodal_policy import MultimodalPolicyService
from app.services.multimodal.multimodal_usage import MultimodalUsageService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

try:
    import io

    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ImageGenerationService:
    @property
    def settings(self):
        return get_settings()

    def __init__(self):
        self.policy_service = MultimodalPolicyService()
        self.usage_service = MultimodalUsageService()

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        self.storage_dir = os.path.join(base_dir, "data", "multimodal_assets")
        os.makedirs(self.storage_dir, exist_ok=True)

    async def generate_image(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        prompt: str,
        size: str = "1024x1024",
        provider: str = "mock",
    ) -> dict:
        # 1. Policy checks (feature flag and safety words check)
        await self.policy_service.check_policy(db, client_id, "image-generation", input_text=prompt)

        # 2. Mock generation logic
        logger.info(f"Generating image using prompt: '{prompt}' and provider: {provider}")

        # Determine image color based on prompt words for a nice visual detail in mock
        color = "blue"
        if "red" in prompt.lower():
            color = "red"
        elif "green" in prompt.lower():
            color = "green"
        elif "yellow" in prompt.lower():
            color = "yellow"

        # Generate binary image bytes
        if HAS_PIL:
            try:
                # Standard mock image size
                width, height = 512, 512
                if size == "256x256":
                    width, height = 256, 256
                elif size == "1024x1024":
                    width, height = 1024, 1024

                image = Image.new("RGB", (width, height), color=color)
                output = io.BytesIO()
                image.save(output, format="PNG")
                image_bytes = output.getvalue()
                mime_type = "image/png"
            except Exception as e:
                logger.error(f"Failed to generate mock PIL image: {e}")
                # Fallback to base64
                image_bytes = base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
                )
                mime_type = "image/png"
        else:
            image_bytes = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            )
            mime_type = "image/png"

        file_hash = hashlib.sha256(image_bytes).hexdigest()
        asset_id = uuid.uuid4()
        storage_path = os.path.join(self.storage_dir, f"{asset_id}.png")

        # Save to disk
        with open(storage_path, "wb") as f:
            f.write(image_bytes)

        # 3. Save as MultimodalAsset with provenance
        asset = MultimodalAsset(
            id=asset_id,
            client_id=client_id,
            asset_type="image",
            storage_path=storage_path,
            file_size_bytes=len(image_bytes),
            mime_type=mime_type,
            file_hash=file_hash,
            provenance=f"generated_{provider}",
            exif_sanitized=True,  # Generated images are clean
            metadata_json={"prompt": prompt, "size": size},
        )
        db.add(asset)
        await db.commit()

        # 4. Log request and usage
        req = await self.usage_service.log_request(
            db, client_id, "image-generation", "completed", output_asset_id=asset_id
        )
        await self.usage_service.record_usage(
            db, client_id, req.id, "image-generation", unit_count=1
        )

        return {
            "asset_id": str(asset_id),
            "prompt": prompt,
            "provider": provider,
            "provenance": asset.provenance,
            "url": f"/v1/multimodal/assets/{asset_id}",
        }
