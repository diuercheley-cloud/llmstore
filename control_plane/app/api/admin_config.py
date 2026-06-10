# Owner: platform-ops
from typing import Any, Dict, List
from app.services.auth import require_admin
from app.services.config_service import get_config_service
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/admin/config",
    tags=["admin-config"],
    dependencies=[Depends(require_admin)]
)

@router.get("/effective", response_model=List[Dict[str, Any]])
async def get_effective_config():
    """
    Retrieve the effective configuration from all sources with secrets redacted.
    """
    service = get_config_service()
    return service.get_effective_config(redact=True)

@router.get("/detailed/{key}", response_model=Dict[str, Any])
async def get_config_detail(key: str):
    """
    Retrieve detailed information for a specific configuration key.
    """
    service = get_config_service()
    detailed = service.get_detailed(key)
    
    # Redact if it's a secret
    if service._is_secret(key):
        detailed.value = "********"
        detailed.default_value = "********" if detailed.default_value is not None else None
        
    # Return as dict for Pydantic/FastAPI
    from dataclasses import asdict
    return asdict(detailed)
