# Owner: commercial-ops

from app.api.dependencies import get_db, require_admin_user
from app.services.runtime.predictive_aiops import PredictiveAIOpsService
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/aiops", tags=["Commercial Predictive AIOps Admin"])


@router.get("/status")
async def get_aiops_status(db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = PredictiveAIOpsService(db)
    return await service.get_status()


@router.get("/forecasts")
async def get_aiops_forecasts(
    limit: int = 50, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)
):
    service = PredictiveAIOpsService(db)
    return await service.get_latest_forecasts(limit)


@router.get("/anomalies")
async def get_aiops_anomalies(
    limit: int = 50, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)
):
    service = PredictiveAIOpsService(db)
    return await service.get_latest_anomalies(limit)


@router.get("/recommendations")
async def get_aiops_recommendations(
    limit: int = 50, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)
):
    service = PredictiveAIOpsService(db)
    return await service.get_latest_recommendations(limit)


@router.get("/risk-trends")
async def get_aiops_risk_trends(
    limit: int = 50, db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)
):
    service = PredictiveAIOpsService(db)
    return await service.get_risk_trends(limit)


@router.post("/run-cycle")
async def run_aiops_cycle(db: AsyncSession = Depends(get_db), admin=Depends(require_admin_user)):
    service = PredictiveAIOpsService(db)
    return await service.run_cycle()
