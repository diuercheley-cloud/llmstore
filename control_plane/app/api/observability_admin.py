from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any, Dict

from app.services.platform_slo import PlatformSLOService
from app.api.deps import get_admin_user # Assuming this exists for security

router = APIRouter(prefix="/admin/observability", tags=["observability"])

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
