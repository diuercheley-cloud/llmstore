import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.services.auth import require_admin
from app.services.providers.registry import (
    get_all_provider_health,
    get_all_provider_statuses,
    get_global_capabilities,
    get_provider,
    get_providers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/providers", tags=["admin"], dependencies=[Depends(require_admin)])

COSTS_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "real-provider-validation" / "costs"


def _load_latest_cost_report():
    if not COSTS_ARTIFACTS_DIR.exists():
        return None
    ts_dirs = sorted([d for d in COSTS_ARTIFACTS_DIR.iterdir() if d.is_dir()], reverse=True)
    if not ts_dirs:
        return None
    latest = ts_dirs[0]
    report_path = latest / "provider-costs.json"
    if not report_path.exists():
        return None
    try:
        with open(report_path) as f:
            data = json.load(f)
    except Exception:
        return None
    return {"timestamp": latest.name, "report": data}


def _sanitize_cost_report(report: dict) -> dict:
    sanitized = {}
    for key, value in report.items():
        if key == "api_key_masked":
            continue
        if isinstance(value, str) and ("sk-" in value or "sk-ant-" in value):
            continue
        if isinstance(value, dict):
            sanitized[key] = _sanitize_cost_report(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_cost_report(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


@router.get("")
async def list_providers():
    statuses = get_all_provider_statuses()
    return [
        {
            "provider_id": s.provider_id,
            "provider_type": s.provider_type,
            "enabled": s.enabled,
            "configured": s.configured,
            "capabilities": s.capabilities.model_dump(),
        }
        for s in statuses
    ]


@router.get("/{provider_id}")
async def get_provider_detail(provider_id: str):
    provider = get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="provider not found")
    caps = provider.capabilities()
    models = await provider.list_models()
    return {
        "provider_id": provider.provider_id,
        "provider_type": provider.provider_type.value,
        "enabled": provider.enabled,
        "configured": provider.configured,
        "capabilities": caps.model_dump(),
        "models": models,
    }


@router.get("/{provider_id}/health")
async def get_provider_health(provider_id: str):
    provider = get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="provider not found")
    try:
        h = await provider.health_check()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "provider_id": provider.provider_id,
        "enabled": provider.enabled,
        "configured": provider.configured,
        "healthy": h.get("healthy"),
        "latency_ms": h.get("latency_ms", 0),
        "last_error_sanitized": h.get("error") if h.get("error") else None,
    }


@router.get("/cost-validation/latest")
async def get_latest_cost_validation():
    report = _load_latest_cost_report()
    if report is None:
        raise HTTPException(status_code=404, detail="no cost validation report found")
    sanitized = _sanitize_cost_report(report)
    return sanitized


@router.get("/capabilities/all")
async def list_all_capabilities():
    providers = get_providers()
    return {
        pid: p.capabilities().model_dump()
        for pid, p in providers.items()
    }
