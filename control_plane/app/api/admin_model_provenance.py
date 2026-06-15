import uuid

from app.models.core.model_provenance import ModelProvenanceRecord
from app.schemas.model_provenance import (
    ModelProvenanceRead,
    WatermarkVerificationRequest,
    WatermarkVerificationResponse,
)
from app.services.model_provenance.service import ModelProvenanceService, StandardOutputWatermarker
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/models", tags=["admin-models-provenance"])


@router.get("/provenance", response_model=list[ModelProvenanceRead])
async def list_model_provenance(db: AsyncSession = Depends(get_db_session)):
    stmt = select(ModelProvenanceRecord).order_by(ModelProvenanceRecord.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/provenance/verify/{record_id}", response_model=ModelProvenanceRead)
async def verify_model_provenance(record_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    service = ModelProvenanceService(db)
    try:
        return await service.verify_provenance(str(record_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/watermark/verify", response_model=WatermarkVerificationResponse)
async def verify_output_watermark(payload: WatermarkVerificationRequest):
    # This doesn't need DB session for basic heuristic
    watermarker = StandardOutputWatermarker()
    result = await watermarker.verify_watermark(payload.text)
    return WatermarkVerificationResponse(
        is_authentic=result["is_authentic"],
        confidence=result["confidence"],
        metadata=result["metadata"],
        detected_id=None,
    )
