import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.billing.revenue_forecasting import RevenueForecastingService
from app.services.billing.financial_anomaly_detection import FinancialAnomalyDetectionService
from app.models.commercial_revenue_forecast import CommercialRevenueForecast
from app.models.commercial_financial_anomaly import CommercialFinancialAnomaly


router = APIRouter(
    prefix="/admin/billing",
    tags=["admin", "billing", "commercial"],
    dependencies=[Depends(require_admin)],
)


class ForecastOverview(BaseModel):
    next_30_days_revenue: float
    next_30_days_cost: float
    next_30_days_margin: float
    confidence: str
    last_updated: datetime


class AnomalyAckRequest(BaseModel):
    explanation: Optional[str] = None


@router.get("/forecast/overview", response_model=ForecastOverview)
async def get_forecast_overview(session: AsyncSession = Depends(get_db_session)):
    svc = RevenueForecastingService(session)
    
    # Get latest forecasts for the main metrics
    stmt = select(CommercialRevenueForecast).order_by(desc(CommercialRevenueForecast.created_at))
    result = await session.execute(stmt)
    forecasts = result.scalars().all()
    
    overview = ForecastOverview(
        next_30_days_revenue=0.0,
        next_30_days_cost=0.0,
        next_30_days_margin=0.0,
        confidence="low",
        last_updated=datetime.utcnow()
    )
    
    found = {"revenue": False, "cost": False, "margin": False}
    for f in forecasts:
        if f.forecast_type == "revenue" and not found["revenue"]:
            overview.next_30_days_revenue = float(f.predicted_amount_brl)
            overview.confidence = f.confidence
            overview.last_updated = f.created_at
            found["revenue"] = True
        elif f.forecast_type == "cost" and not found["cost"]:
            overview.next_30_days_cost = float(f.predicted_amount_brl)
            found["cost"] = True
        elif f.forecast_type == "margin" and not found["margin"]:
            overview.next_30_days_margin = float(f.predicted_amount_brl)
            found["margin"] = True
            
        if all(found.values()):
            break
            
    return overview


@router.post("/forecast/run")
async def run_forecast(session: AsyncSession = Depends(get_db_session)):
    svc = RevenueForecastingService(session)
    r = await svc.forecast_revenue()
    c = await svc.forecast_cost()
    m = await svc.forecast_margin()
    q = await svc.forecast_qos_billing()
    return {"status": "success", "forecasts_created": 4}


@router.get("/forecast/records")
async def list_forecast_records(
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialRevenueForecast).order_by(desc(CommercialRevenueForecast.created_at)).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/anomalies")
async def list_anomalies(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialFinancialAnomaly).order_by(desc(CommercialFinancialAnomaly.detected_at))
    if status:
        stmt = stmt.where(CommercialFinancialAnomaly.status == status)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/anomalies/run")
async def run_anomaly_detection(session: AsyncSession = Depends(get_db_session)):
    svc = FinancialAnomalyDetectionService(session)
    r = await svc.detect_revenue_anomalies()
    c = await svc.detect_cost_anomalies()
    m = await svc.detect_margin_anomalies()
    w = await svc.detect_wallet_debit_anomalies()
    q = await svc.detect_qos_billing_anomalies()
    d = await svc.detect_dispute_anomalies()
    total = len(r) + len(c) + len(m) + len(w) + len(q) + len(d)
    return {"status": "success", "anomalies_detected": total}


@router.post("/anomalies/{anomaly_id}/ack")
async def acknowledge_anomaly(
    anomaly_id: uuid.UUID,
    req: AnomalyAckRequest,
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialFinancialAnomaly).where(CommercialFinancialAnomaly.id == anomaly_id)
    result = await session.execute(stmt)
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.status = "acknowledged"
    if req.explanation:
        anomaly.explanation = (anomaly.explanation or "") + f" | ACK: {req.explanation}"
    await session.commit()
    return anomaly


@router.post("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: uuid.UUID,
    req: AnomalyAckRequest,
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialFinancialAnomaly).where(CommercialFinancialAnomaly.id == anomaly_id)
    result = await session.execute(stmt)
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.status = "resolved"
    if req.explanation:
        anomaly.explanation = (anomaly.explanation or "") + f" | RESOLVED: {req.explanation}"
    await session.commit()
    return anomaly


@router.post("/anomalies/{anomaly_id}/ignore")
async def ignore_anomaly(
    anomaly_id: uuid.UUID,
    req: AnomalyAckRequest,
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(CommercialFinancialAnomaly).where(CommercialFinancialAnomaly.id == anomaly_id)
    result = await session.execute(stmt)
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.status = "ignored"
    if req.explanation:
        anomaly.explanation = (anomaly.explanation or "") + f" | IGNORED: {req.explanation}"
    await session.commit()
    return anomaly
