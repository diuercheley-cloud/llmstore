import uuid
from typing import Any

from app.schemas.marketplace import (
    AgentManifest,
    ApproveInstallRequest,
    InstallDryRunRequest,
    InstallDryRunResponse,
)
from app.services.marketplace.service import MarketplaceService
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/marketplace", tags=["admin-marketplace"])


@router.get("/agents")
async def list_marketplace_agents(db: AsyncSession = Depends(get_db_session)):
    service = MarketplaceService(db)
    items = await service.list_available_agents()

    # Simple mapping for this prototype
    return [
        {
            "id": str(i.id),
            "publisher_id": str(i.publisher_id),
            "name": i.name,
            "version": i.version,
            "description": i.description,
            "risk_level": i.risk_level,
            "price_brl": i.price_brl,
            "is_verified": False,
            "permissions": i.manifest_json.get("permissions", []),
            "attestation_status": "verified" if i.manifest_json.get("signature") else "untrusted",
        }
        for i in items
    ]


@router.post("/validate")
async def validate_marketplace_package(
    manifest: dict[str, Any], db: AsyncSession = Depends(get_db_session)
):
    service = MarketplaceService(db)
    try:
        return await service.validate_package(manifest)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/install/dry-run", response_model=InstallDryRunResponse)
async def install_dry_run(
    request: InstallDryRunRequest, db: AsyncSession = Depends(get_db_session)
):
    service = MarketplaceService(db)
    # Mock manifest for simulation
    mock_manifest = AgentManifest(
        name="Demo Agent",
        version="1.0.0",
        author="External Dev",
        description="Loaded from package URL",
        permissions=["filesystem:write"] if "dangerous" in request.package_url else ["chat:read"],
    )
    return await service.install_dry_run(mock_manifest, request.package_url)


@router.post("/install/approve")
async def approve_installation(
    request: ApproveInstallRequest, db: AsyncSession = Depends(get_db_session)
):
    # In a real system, this would finalize the download and register local agent
    return {
        "status": "success",
        "agent_id": str(uuid.uuid4()),
        "message": "Agent installed and sandbox provisioned.",
    }
