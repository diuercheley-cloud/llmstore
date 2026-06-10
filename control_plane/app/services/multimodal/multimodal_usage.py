import uuid
from typing import Any, Dict, List

from app.models.core.multimodal import MultimodalRequest, MultimodalUsageEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class MultimodalUsageService:
    def __init__(self):
        pass

    def calculate_cost(self, feature: str, unit_count: int) -> float:
        """
        Return cost estimation:
        - vision: $0.02 per image
        - image-generation: $0.05 per image
        - speech-to-text: $0.006 per second
        - audio-streaming: $0.01 per second
        """
        rates = {
            "vision": 0.02,
            "image-generation": 0.05,
            "speech-to-text": 0.006,
            "audio-streaming": 0.01
        }
        return rates.get(feature, 0.0) * unit_count

    async def log_request(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        request_type: str,
        status: str,
        input_asset_id: uuid.UUID = None,
        output_asset_id: uuid.UUID = None,
        error_message: str = None,
        metadata_json: dict = None
    ) -> MultimodalRequest:
        req = MultimodalRequest(
            id=uuid.uuid4(),
            client_id=client_id,
            request_type=request_type,
            status=status,
            input_asset_id=input_asset_id,
            output_asset_id=output_asset_id,
            error_message=error_message,
            metadata_json=metadata_json or {}
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return req

    async def record_usage(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        request_id: uuid.UUID,
        feature: str,
        unit_count: int
    ) -> MultimodalUsageEvent:
        cost = self.calculate_cost(feature, unit_count)
        usage = MultimodalUsageEvent(
            id=uuid.uuid4(),
            client_id=client_id,
            request_id=request_id,
            feature=feature,
            unit_count=unit_count,
            estimated_cost=cost
        )
        db.add(usage)
        await db.commit()
        await db.refresh(usage)
        return usage

    async def get_usage_summary(self, db: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(MultimodalUsageEvent).order_by(MultimodalUsageEvent.created_at.desc())
        res = await db.execute(stmt)
        events = res.scalars().all()
        
        summary = []
        for e in events:
            summary.append({
                "id": str(e.id),
                "client_id": str(e.client_id),
                "request_id": str(e.request_id) if e.request_id else None,
                "feature": e.feature,
                "unit_count": e.unit_count,
                "estimated_cost": e.estimated_cost,
                "created_at": e.created_at.isoformat()
            })
        return summary
