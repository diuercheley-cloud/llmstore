# Owner: commercial-ops
from typing import Optional

from app.api.deps import get_admin_user, get_db
from app.core.config import get_settings
from app.models.commercial.commercial_capacity import (
    CommercialAutoscalingRecommendation,
    CommercialCapacityForecast,
    CommercialCapacitySnapshot,
)
from app.services.routing.commercial_autoscaling import generate_autoscaling_recommendations
from app.services.routing.commercial_capacity_forecasting import forecast_capacity
from app.services.routing.commercial_capacity_monitor import (
    capture_capacity_snapshot,
    summarize_cluster_capacity,
)
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/routing/capacity", tags=["commercial_capacity"])

@router.get("/overview")
async def get_capacity_overview(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    settings = get_settings()
    cid = cluster_id or settings.cluster_id
    
    summary = await summarize_cluster_capacity(db, cid)
    
    # Get latest snapshots for detailed view
    stmt = select(CommercialCapacitySnapshot).where(
        CommercialCapacitySnapshot.cluster_id == cid
    ).order_by(CommercialCapacitySnapshot.timestamp.desc()).limit(50)
    
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    return {
        "summary": summary,
        "snapshots": snapshots,
        "enabled": settings.commercial_capacity_planning_enabled,
        "mode": settings.commercial_autoscaling_mode
    }

@router.get("/forecast")
async def get_capacity_forecast(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    settings = get_settings()
    cid = cluster_id or settings.cluster_id
    
    stmt = select(CommercialCapacityForecast).where(
        CommercialCapacityForecast.cluster_id == cid
    ).order_by(CommercialCapacityForecast.created_at.desc()).limit(20)
    
    result = await db.execute(stmt)
    forecasts = result.scalars().all()
    
    return {
        "cluster_id": cid,
        "forecasts": forecasts
    }

@router.get("/recommendations")
async def get_autoscaling_recommendations(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    settings = get_settings()
    cid = cluster_id or settings.cluster_id
    
    stmt = select(CommercialAutoscalingRecommendation).where(
        CommercialAutoscalingRecommendation.cluster_id == cid
    ).order_by(CommercialAutoscalingRecommendation.created_at.desc()).limit(20)
    
    result = await db.execute(stmt)
    recs = result.scalars().all()
    
    return {
        "cluster_id": cid,
        "recommendations": recs
    }

@router.get("/anomalies")
async def get_capacity_anomalies(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    return {"anomalies": []} # Placeholder for Phase 21

@router.post("/capture")
async def trigger_capacity_capture(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    settings = get_settings()
    cid = cluster_id or settings.cluster_id
    snapshots = await capture_capacity_snapshot(db, cid)
    return {"status": "ok", "captured_count": len(snapshots)}

@router.post("/rebuild-forecast")
async def trigger_rebuild_forecast(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    settings = get_settings()
    cid = cluster_id or settings.cluster_id
    
    # Rebuild for cluster
    f = await forecast_capacity(db, cid)
    
    # Also trigger recommendations
    recs = await generate_autoscaling_recommendations(db, cid)
    
    return {
        "status": "ok", 
        "forecast_id": str(f.id) if f else None,
        "recommendations_generated": len(recs)
    }

@router.get("/export")
async def export_capacity_data(
    format: str = Query("json", pattern="^(json|csv|html)$"),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_admin_user),
    cluster_id: Optional[str] = None
):
    settings = get_settings()
    cid = cluster_id or settings.cluster_id
    
    stmt = select(CommercialCapacitySnapshot).where(
        CommercialCapacitySnapshot.cluster_id == cid
    ).order_by(CommercialCapacitySnapshot.timestamp.desc()).limit(1000)
    
    result = await db.execute(stmt)
    snapshots = result.scalars().all()
    
    if format == "json":
        return snapshots
    
    elif format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "provider", "model", "rpm", "concurrency", "latency", "sla_violation"])
        for s in snapshots:
            writer.writerow([s.id, s.timestamp, s.provider, s.model, s.requests_per_minute, s.concurrent_requests, s.avg_latency_ms, s.sla_violation_rate])
        return Response(content=output.getvalue(), media_type="text/csv")
        
    elif format == "html":
        html = "<html><body><h1>Capacity Export</h1><table>"
        html += "<tr><th>Timestamp</th><th>Provider</th><th>Model</th><th>RPM</th><th>SLA Violation %</th></tr>"
        for s in snapshots:
            html += f"<tr><td>{s.timestamp}</td><td>{s.provider}</td><td>{s.model}</td><td>{s.requests_per_minute:.2f}</td><td>{s.sla_violation_rate:.2f}%</td></tr>"
        html += "</table></body></html>"
        return Response(content=html, media_type="text/html")
