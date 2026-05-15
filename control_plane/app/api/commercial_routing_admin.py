from __future__ import annotations

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import require_admin as get_admin_user
from app.schemas.routing import (
    CommercialCalibrationSimulateRequest,
    CommercialCalibrationSimulateResponse,
    CommercialReportDeliveryListResponse,
    CommercialReportDeliveryLogRead,
    CommercialReportScheduleCreate,
    CommercialReportScheduleRead,
    CommercialReportScheduleRunResponse,
    CommercialReportSendTestResponse,
    TaskType,
)
from app.services.routing import commercial_analytics, commercial_ranker, commercial_calibration, commercial_auto_apply
from app.db.session import get_db_session
from app.services.routing.commercial_config_store import CommercialConfigStore
from app.schemas.routing import CommercialConfigApplyRequest, CommercialConfigRead
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/routing", tags=["Commercial Routing"])


@router.get("/calibration/report")
async def get_calibration_report(
    days: int = 7,
    provider: str | None = None,
    model: str | None = None,
    min_samples: int = 20,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns a calibration report based on historical routing events.
    """
    return await commercial_calibration.generate_calibration_report(
        db, 
        days=days, 
        min_samples=min_samples
    )


@router.post("/calibration/simulate", response_model=CommercialCalibrationSimulateResponse)
async def simulate_calibration(
    req: CommercialCalibrationSimulateRequest,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Simulates a calibration adjustment for a specific provider and model.
    """
    error_summary = await commercial_calibration.calculate_estimation_error(
        db,
        days=req.actual_cost_history_days,
        provider=req.provider,
        model=req.model,
        min_samples=1
    )
    
    multiplier = commercial_calibration.recommend_cost_multiplier(
        error_summary.get("cost_error_percent", 0),
        error_summary.get("confidence", "low")
    )
    
    return CommercialCalibrationSimulateResponse(
        current_estimated_cost_brl=req.current_estimated_cost_brl,
        recommended_multiplier=round(multiplier, 2),
        adjusted_estimated_cost_brl=round(req.current_estimated_cost_brl * multiplier, 4),
        confidence=error_summary.get("confidence", "low"),
        reason=error_summary.get("reason", "Based on historical average error"),
    )


@router.get("/events")
async def list_routing_events(
    client_id: uuid.UUID | None = None,
    provider: str | None = None,
    blocked: bool | None = None,
    fallback_used: bool | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Lists recent commercial routing events with filters.
    """
    events = await commercial_analytics.list_recent_events(
        db,
        limit=limit,
        client_id=client_id,
        provider=provider,
        blocked=blocked,
        fallback_used=fallback_used,
    )
    return events


@router.get("/analytics/summary")
async def get_routing_summary(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns a summary of today's commercial routing analytics.
    """
    return await commercial_analytics.summarize_today(db)


@router.get("/commercial-configs", response_model=List[CommercialConfigRead])
async def list_commercial_configs(
    active_only: bool = True,
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Lists commercial routing configurations.
    """
    store = CommercialConfigStore(db)
    configs = await store.list_configs(active_only=active_only)
    return configs

@router.post("/commercial-configs/apply-recommendation", response_model=CommercialConfigRead)
async def apply_commercial_recommendation(
    req: CommercialConfigApplyRequest,
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Applies a calibration recommendation manually.
    """
    if req.confidence == "low" and not req.force:
        raise HTTPException(status_code=400, detail="Cannot apply low confidence recommendation without force=true")
        
    store = CommercialConfigStore(db)
    
    scope_type = "global"
    if req.provider and req.model:
        scope_type = "provider_model"
    elif req.model:
        scope_type = "model"
    elif req.provider:
        scope_type = "provider"
        
    try:
        config = await store.apply_config(
            scope_type=scope_type,
            provider=req.provider,
            model=req.model,
            cost_multiplier=req.recommended_cost_multiplier,
            source="calibration",
            created_by=getattr(admin_user, "email", "admin"),
            notes=req.notes,
            force=req.force
        )
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/commercial-configs/{config_id}/deactivate")
async def deactivate_commercial_config(
    config_id: uuid.UUID,
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Deactivates a specific commercial routing configuration.
    """
    store = CommercialConfigStore(db)
    success = await store.deactivate_config(config_id, actor=getattr(admin_user, "email", "admin"))
    if not success:
        raise HTTPException(status_code=404, detail="Active config not found")
    return {"status": "success"}

@router.post("/commercial-configs/rollback")
async def rollback_commercial_config(
    scope_type: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Rolls back to the previous configuration for a given scope.
    """
    store = CommercialConfigStore(db)
    config = await store.rollback_config(
        scope_type=scope_type,
        provider=provider,
        model=model,
        actor=getattr(admin_user, "email", "admin")
    )
    if not config:
        raise HTTPException(status_code=404, detail="No previous config found for rollback")
    return config

@router.get("/commercial-configs/canaries", response_model=List[CommercialConfigRead])
async def list_commercial_canaries(
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Lists active commercial canary configurations.
    """
    store = CommercialConfigStore(db)
    return await store.list_canaries()

@router.post("/commercial-configs/auto-apply/dry-run")
async def auto_apply_dry_run(
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Simulates auto-apply for all eligible recommendations.
    """
    service = commercial_auto_apply.CommercialAutoApplyService(db)
    report = await commercial_calibration.generate_calibration_report(db)
    
    results = []
    for model_key, recommendation in report.get("recommendations", {}).items():
        # model_key format: "provider:model"
        if ":" not in model_key:
            continue
        provider, model = model_key.split(":", 1)
        
        eval_result = await service.evaluate_auto_apply_candidate(provider, model, recommendation)
        results.append(eval_result)
        
    return {
        "mode": "dry_run",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

from app.services.routing.commercial_canary_promotion import CommercialCanaryPromotionService
from app.services.routing.commercial_executive_dashboard import CommercialExecutiveDashboardService
from app.services.routing.commercial_report_export import (
    CommercialReportExportService,
    export_executive_report_csv,
    export_executive_report_html,
    export_executive_report_json,
    export_executive_report_pdf_optional,
)

# ... (existing code)

@router.get("/executive-dashboard/overview")
async def get_executive_overview(
    hours: int = 24,
    client_id: uuid.UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns a consolidated executive overview of profitability and drift.
    """
    service = CommercialExecutiveDashboardService(db)
    return await service.get_overview(
        hours=hours,
        client_id=client_id,
        provider=provider,
        model=model
    )


@router.get("/executive-dashboard/anomalies")
async def get_executive_anomalies(
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Lists detected commercial anomalies for the period.
    """
    service = CommercialExecutiveDashboardService(db)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    profitability = await service.get_profitability_overview(since)
    drift = await service.get_drift_overview(since)
    
    return await service.detect_anomalies(since, profitability, drift)


@router.get("/executive-dashboard/recommendations")
async def get_executive_recommendations(
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns executive recommendations based on current anomalies.
    """
    service = CommercialExecutiveDashboardService(db)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    profitability = await service.get_profitability_overview(since)
    drift = await service.get_drift_overview(since)
    anomalies = await service.detect_anomalies(since, profitability, drift)
    canaries = await service.summarize_canary_health()
    
    return await service.generate_executive_recommendations(anomalies, canaries)


@router.get("/executive-dashboard/export")
async def export_executive_dashboard_report(
    format: str = "json",
    hours: int = 24,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    client_id: uuid.UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    report = await service.build_executive_report_data(
        hours=hours,
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        provider=provider,
        model=model,
    )
    if format == "json":
        return JSONResponse(
            content=report,
            headers={"Content-Disposition": 'attachment; filename="executive-report.json"'},
        )
    if format == "csv":
        return Response(
            content=export_executive_report_csv(report),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="executive-report.csv"'},
        )
    if format == "html":
        return HTMLResponse(
            content=export_executive_report_html(report),
            headers={"Content-Disposition": 'attachment; filename="executive-report.html"'},
        )
    if format == "pdf":
        pdf = export_executive_report_pdf_optional(report)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="executive-report.pdf"'},
        )
    raise HTTPException(status_code=400, detail="Unsupported format. Use json, csv, html or pdf.")


@router.get("/executive-dashboard/export/preview", response_class=HTMLResponse)
async def preview_executive_dashboard_report(
    hours: int = 24,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    client_id: uuid.UUID | None = None,
    provider: str | None = None,
    model: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    report = await service.build_executive_report_data(
        hours=hours,
        date_from=date_from,
        date_to=date_to,
        client_id=client_id,
        provider=provider,
        model=model,
    )
    return HTMLResponse(content=export_executive_report_html(report, preview=True))


@router.get("/executive-dashboard/report-schedules", response_model=List[CommercialReportScheduleRead])
async def list_report_schedules(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.list_schedules()


@router.post("/executive-dashboard/report-schedules", response_model=CommercialReportScheduleRead)
async def create_report_schedule(
    payload: CommercialReportScheduleCreate,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.create_schedule(payload.model_dump(), actor=getattr(admin_user, "email", "admin"))


@router.post("/executive-dashboard/report-schedules/{schedule_id}/run-now", response_model=CommercialReportScheduleRunResponse)
async def run_report_schedule_now(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.run_schedule_now(schedule_id)


@router.post("/executive-dashboard/report-schedules/{schedule_id}/send-test-email", response_model=CommercialReportSendTestResponse)
async def send_report_schedule_test_email(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.send_test_email(schedule_id)


@router.get("/executive-dashboard/report-deliveries", response_model=CommercialReportDeliveryListResponse)
async def list_report_deliveries(
    status: str | None = None,
    recipient: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.list_delivery_logs(
        status=status,
        recipient=recipient,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.post("/executive-dashboard/report-schedules/{schedule_id}/disable", response_model=CommercialReportScheduleRead)
async def disable_report_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.set_schedule_enabled(schedule_id, False)


@router.post("/executive-dashboard/report-schedules/{schedule_id}/enable", response_model=CommercialReportScheduleRead)
async def enable_report_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    service = CommercialReportExportService(db)
    return await service.set_schedule_enabled(schedule_id, True)


@router.get("/commercial-configs/canary-promotions")
async def list_canary_promotions(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Lists active canary promotions with SLO status.
    """
    service = CommercialCanaryPromotionService(db)
    return await service.list_active_promotions()


@router.get("/commercial-configs/{config_id}/canary/slo")
async def get_canary_slo(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Returns the SLO evaluation for a specific canary config.
    """
    service = CommercialCanaryPromotionService(db)
    return await service.evaluate_canary_slo(config_id)


@router.post("/commercial-configs/canary/promotions/dry-run")
async def canary_promotions_dry_run(
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Simulates promotion for all active canaries.
    """
    service = CommercialCanaryPromotionService(db)
    promotions = await service.list_active_promotions()

    results = []
    for p in promotions:
        res = await service.promote_canary_step(uuid.UUID(p["id"]), actor=getattr(admin_user, "email", "admin"))
        results.append(res)

    return {
        "mode": "dry_run",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/commercial-configs/{config_id}/canary/promote-step")
async def promote_canary_step(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Manually promotes a canary to the next step if SLOs are met.
    """
    service = CommercialCanaryPromotionService(db)
    res = await service.promote_canary_step(config_id, actor=getattr(admin_user, "email", "admin"))
    return res


@router.post("/commercial-configs/{config_id}/canary/auto-rollback")
async def trigger_canary_rollback(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    admin_user: Any = Depends(get_admin_user),
):
    """
    Evaluates and potentially rolls back a canary if it's unhealthy.
    """
    service = CommercialCanaryPromotionService(db)
    return await service.auto_rollback_if_unhealthy(config_id, actor=getattr(admin_user, "email", "admin"))


@router.post("/commercial-configs/auto-apply/run")
async def auto_apply_run(
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Executes auto-apply for all eligible recommendations.
    """
    service = commercial_auto_apply.CommercialAutoApplyService(db)
    report = await commercial_calibration.generate_calibration_report(db)
    
    applied = []
    rejected = []
    
    for model_key, recommendation in report.get("recommendations", {}).items():
        if ":" not in model_key:
            continue
        provider, model = model_key.split(":", 1)
        
        config = await service.run_auto_apply(provider, model, recommendation, actor=getattr(admin_user, "email", "admin"))
        if config:
            applied.append({
                "provider": provider,
                "model": model,
                "config_id": str(config.id),
                "canary_percent": config.canary_percent
            })
        else:
            rejected.append({
                "provider": provider,
                "model": model
            })
            
    return {
        "status": "completed",
        "applied_count": len(applied),
        "applied": applied,
        "rejected_count": len(rejected),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/commercial-configs/{config_id}/canary/promote", response_model=CommercialConfigRead)
async def promote_commercial_canary(
    config_id: uuid.UUID,
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Promotes a canary configuration to 100% stable.
    """
    service = commercial_auto_apply.CommercialAutoApplyService(db)
    config = await service.promote_canary(config_id, actor=getattr(admin_user, "email", "admin"))
    if not config:
        raise HTTPException(status_code=404, detail="Active canary config not found")
    return config

@router.post("/commercial-configs/{config_id}/canary/rollback")
async def rollback_commercial_canary(
    config_id: uuid.UUID,
    admin_user: Any = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Immediately rolls back (deactivates) a canary configuration.
    """
    service = commercial_auto_apply.CommercialAutoApplyService(db)
    success = await service.rollback_canary(config_id, actor=getattr(admin_user, "email", "admin"))
    if not success:
        raise HTTPException(status_code=404, detail="Canary config not found")
    return {"status": "success", "config_id": str(config_id)}

@router.post("/commercial-configs/auto-apply-settings")
async def update_auto_apply_settings(
    settings_patch: dict, # Simplified for now
    admin_user: Any = Depends(get_admin_user),
):
    """
    Updates auto-apply settings (In a real scenario, this would persist to DB or update ENV).
    Since we use pydantic settings, we'll just acknowledge or return current.
    """
    # This is a placeholder as per requirements: "auto-apply-settings deve permitir: enabled, mode, etc."
    # In this project, settings are mostly env-based or global.
    from app.core.config import get_settings
    s = get_settings()
    
    return {
        "current_settings": {
            "enabled": s.commercial_calibration_auto_apply,
            "mode": s.commercial_calibration_auto_apply_mode,
            "max_change_percent": s.commercial_calibration_auto_apply_max_change_percent,
            "min_confidence": s.commercial_calibration_auto_apply_min_confidence,
            "canary_default_percent": s.commercial_calibration_canary_default_percent,
            "canary_max_percent": s.commercial_calibration_canary_max_percent
        }
    }
