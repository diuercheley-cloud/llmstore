from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session
from app.services.observability.service import AdvancedObservabilityService
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/admin/observability", tags=["admin-observability"])


@router.get("/metrics")
async def get_observability_metrics(
    service: AdvancedObservabilityService = Depends(AdvancedObservabilityService)
):
    """
    Returns the latest collected metrics including eBPF data if available.
    """
    await service.collect_and_analyze()
    return {
        "metrics": service.recent_metrics,
        "ebpf_status": service.get_ebpf_status(),
        "summary": service.get_summary()
    }


@router.get("/anomalies")
async def get_detected_anomalies(
    service: AdvancedObservabilityService = Depends(AdvancedObservabilityService)
):
    """
    Lists recent anomalies detected in the system.
    """
    return service.recent_anomalies


@router.post("/anomalies/dry-run")
async def anomaly_detection_dry_run(
    metric_name: str,
    values: List[float],
    z_threshold: float = Query(3.0),
    service: AdvancedObservabilityService = Depends(AdvancedObservabilityService)
):
    """
    Simulates anomaly detection on a series of values.
    """
    service.detector.z_threshold = z_threshold
    anomalies = service.detector.dry_run(metric_name, values)
    
    return {
        "metric_name": metric_name,
        "input_count": len(values),
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies
    }
