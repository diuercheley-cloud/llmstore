import logging
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


@router.get("/capabilities/all")
async def list_all_capabilities():
    providers = get_providers()
    return {
        pid: p.capabilities().model_dump()
        for pid, p in providers.items()
    }
