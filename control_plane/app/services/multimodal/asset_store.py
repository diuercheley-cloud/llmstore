import hashlib
import io
import uuid
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.multimodal import MultimodalAsset
from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class AssetStore:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        # Setup upload storage directory
        self.storage_dir = Path(getattr(self.settings, "rag_storage_dir", "/tmp")) / "multimodal_uploads"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_image_exif(self, file_bytes: bytes, mime_type: str) -> Tuple[bytes, bool]:
        """Strips EXIF metadata from images to prevent metadata leaks."""
        if not mime_type.startswith("image/"):
            return file_bytes, False
        try:
            img = Image.open(io.BytesIO(file_bytes))
            out = io.BytesIO()
            # Save without passing exif/info parameters to strip EXIF data
            fmt = img.format if img.format else "PNG"
            img.save(out, format=fmt)
            return out.getvalue(), True
        except Exception:
            # Fallback if image processing fails
            return file_bytes, False

    async def store_asset(
        self,
        client_id: uuid.UUID,
        tenant_id: str,
        asset_type: str,
        file_bytes: bytes,
        mime_type: str,
        provenance: str = "uploaded"
    ) -> MultimodalAsset:
        """Stores multimodal asset locally, sanitizes EXIF, and records in database."""
        if not self.settings.multimodal_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multimodal service is disabled"
            )

        # 1. Strip EXIF data if image
        sanitized_bytes, exif_sanitized = self._sanitize_image_exif(file_bytes, mime_type)

        # 2. Compute file hash
        file_hash = hashlib.sha256(sanitized_bytes).hexdigest()

        # 3. Store file to disk
        asset_id = uuid.uuid4()
        file_extension = mime_type.split("/")[-1].split("+")[0]
        file_name = f"{asset_id}.{file_extension}"
        storage_path = self.storage_dir / file_name

        with open(storage_path, "wb") as f:
            f.write(sanitized_bytes)

        # 4. Save to Database
        asset = MultimodalAsset(
            id=asset_id,
            client_id=client_id,
            tenant_id=tenant_id,
            asset_type=asset_type,
            storage_path=str(storage_path),
            file_size_bytes=len(sanitized_bytes),
            mime_type=mime_type,
            file_hash=file_hash,
            provenance=provenance,
            exif_sanitized=exif_sanitized,
            redaction_status="completed" if exif_sanitized else "skipped",
            created_at=utc_now(),
            metadata_json={"provider": "local"}
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def get_asset(self, asset_id: uuid.UUID, tenant_id: str) -> Optional[MultimodalAsset]:
        """Retrieves asset with strict tenant isolation check."""
        if not self.settings.multimodal_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multimodal service is disabled"
            )

        res = await self.db.execute(
            select(MultimodalAsset).where(MultimodalAsset.id == asset_id)
        )
        asset = res.scalar_one_or_none()
        if not asset:
            return None

        # Tenant isolation boundary check
        if asset.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant isolation violation"
            )

        return asset
