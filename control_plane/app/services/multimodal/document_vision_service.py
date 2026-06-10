import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.core.multimodal import MultimodalAnalysisEvent, MultimodalRequest, MultimodalUsageEvent
from app.services.multimodal.asset_store import AssetStore
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


class DocumentVisionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.asset_store = AssetStore(db)

    async def analyze_document(
        self,
        client_id: uuid.UUID,
        tenant_id: str,
        asset_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Extracts text and metadata from document assets with feature flag enforcement."""
        if not self.settings.multimodal_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multimodal service is disabled"
            )
        if not self.settings.document_vision_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document vision service is disabled"
            )

        # 1. Fetch asset with tenant validation
        asset = await self.asset_store.get_asset(asset_id, tenant_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )

        if asset.mime_type != "application/pdf" and not asset.mime_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Asset is not a valid document (PDF or image)"
            )

        # 2. Track MultimodalRequest
        req = MultimodalRequest(
            client_id=client_id,
            request_type="document_vision",
            status="completed",
            input_asset_id=asset_id,
            created_at=utc_now(),
            metadata_json={"provider": "mock"}
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)

        # 3. Simulate text extraction & metadata sanitization (Mock provider)
        analysis_result = {
            "extracted_text": "Mock document content extracted from PDF file. All compliance guidelines are met.",
            "sanitized_metadata": {
                "author": "[REDACTED]",
                "creator": "[REDACTED]",
                "creation_date": "2026-05-30"
            },
            "pages": 1,
            "provider": "mock"
        }

        # 4. Save MultimodalAnalysisEvent
        analysis_event = MultimodalAnalysisEvent(
            client_id=client_id,
            tenant_id=tenant_id,
            asset_id=asset_id,
            analysis_type="document_vision",
            results=analysis_result,
            created_at=utc_now()
        )
        self.db.add(analysis_event)

        # 5. Save MultimodalUsageEvent
        usage = MultimodalUsageEvent(
            client_id=client_id,
            request_id=req.id,
            feature="document_vision",
            unit_count=1,
            estimated_cost=0.02,
            created_at=utc_now()
        )
        self.db.add(usage)
        await self.db.commit()

        return analysis_result
