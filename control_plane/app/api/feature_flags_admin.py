# Owner: platform-ops
from typing import Any

from app.services.auth import require_admin
from app.services.feature_flag_registry import FeatureFlagRegistryService
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(
    prefix="/admin/feature-flags",
    tags=["admin-feature-flags"],
    dependencies=[Depends(require_admin)],
)

service = FeatureFlagRegistryService()


@router.get("", response_model=list[dict[str, Any]])
async def list_feature_flags():
    """
    Retrieve all registered feature flags.
    """
    return service.get_all_flags()


@router.get("/deprecated", response_model=list[dict[str, Any]])
async def list_deprecated_flags():
    """
    Retrieve all deprecated feature flags.
    """
    return service.get_deprecated_flags()


@router.get("/conflicts", response_model=list[dict[str, Any]])
async def list_active_conflicts():
    """
    Detect currently active feature flag conflicts based on active environment settings.
    """
    return service.detect_active_conflicts()


@router.post("/validate")
async def validate_registry():
    """
    Validate the feature flag registry against policy rules.
    """
    is_valid, errors = service.validate_registry()
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Feature flag registry validation failed.", "errors": errors},
        )
    return {"status": "valid", "message": "All feature flags are compliant."}


@router.get("/{name}", response_model=dict[str, Any])
async def get_flag_details(name: str):
    """
    Retrieve detailed metadata for a specific feature flag.
    """
    flag = service.get_flag_by_name(name)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{name}' not found in registry.",
        )
    return flag
