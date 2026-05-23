# Owner: platform-ops
from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any, Dict

from app.services.platform_slo import PlatformSLOService
from app.services.visual_observability import VisualObservabilityService
from app.db.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/observability", tags=["observability"])

@router.get("/dashboard-links")
async def get_dashboard_links() -> List[Dict[str, str]]:
    service = VisualObservabilityService()
    return service.get_dashboard_links()

@router.get("/error-budget")
async def get_error_budget() -> Dict[str, Any]:
    service = VisualObservabilityService()
    return await service.get_error_budget()

@router.get("/incidents/timeline")
async def get_incident_timeline(limit: int = 50) -> List[Dict[str, Any]]:
    service = VisualObservabilityService()
    return await service.get_incident_timeline(limit=limit)

@router.get("/metrics/derived")
async def get_metrics_derived() -> Dict[str, Any]:
    service = VisualObservabilityService()
    return service.get_metrics_derived()

@router.get("/slo")
async def get_slo_report() -> Dict[str, Any]:
    """
    Returns the current Service Level Objectives (SLO) report.
    """
    service = PlatformSLOService()
    return service.get_slo_report()

@router.get("/platform-health")
async def get_platform_health() -> Dict[str, Any]:
    """
    Returns the aggregated platform health status.
    """
    service = PlatformSLOService()
    return service.get_platform_health()
