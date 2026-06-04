# Owner: Architecture
# Surface: admin

from typing import Any, Dict, List

from app.services.auth import require_admin
from app.services.supported_surface import SupportedSurfaceService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    prefix="/admin/support/surface",
    tags=["admin", "support", "surface"],
    dependencies=[Depends(require_admin)],
)

# Instantiate service once
service = SupportedSurfaceService()

@router.get("", response_model=List[Dict[str, Any]])
async def get_all_surfaces():
    """
    Retrieve all platform capabilities and their support classifications.
    """
    return service.get_all_capabilities()

@router.get("/status/{status}", response_model=List[Dict[str, Any]])
async def get_surfaces_by_status(status: str):
    """
    Retrieve all platform capabilities matching a specific support status.
    """
    valid_statuses = {"supported", "beta", "experimental", "advisory", "deprecated", "internal", "placeholder"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of {sorted(list(valid_statuses))}"
        )
    return service.get_capabilities_by_status(status)

@router.get("/{id}", response_model=Dict[str, Any])
async def get_surface_by_id(id: str):
    """
    Retrieve details for a single platform capability by its ID.
    """
    cap = service.get_capability_by_id(id)
    if not cap:
        raise HTTPException(
            status_code=404,
            detail=f"Capability with ID '{id}' not found."
        )
    return cap
