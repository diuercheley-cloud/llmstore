import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.managed_control_plane import (
    ManagedOrganization,
    ManagedOrganizationCreate,
    ManagedWorkspace,
    ManagedWorkspaceCreate,
    ManagedAppliance,
    ApplianceEnrollmentToken,
    ApplianceEnrollRequest,
    ApplianceEnrollResponse,
    ApplianceHeartbeatPayload,
)
from app.services.managed_control_plane import ManagedControlPlaneService
from app.services.auth import require_admin
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/managed",
    tags=["managed_control_plane"],
)

# --- Organizations ---

@router.post("/organizations", response_model=ManagedOrganization, dependencies=[Depends(require_admin)])
async def create_organization(
    org_in: ManagedOrganizationCreate,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    return await service.create_organization(org_in)

@router.get("/organizations", response_model=List[ManagedOrganization], dependencies=[Depends(require_admin)])
async def list_organizations(
    session: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select
    from app.models.managed_control_plane import ManagedOrganization
    
    stmt = select(ManagedOrganization)
    result = await session.execute(stmt)
    return result.scalars().all()

# --- Workspaces ---

@router.post("/workspaces", response_model=ManagedWorkspace, dependencies=[Depends(require_admin)])
async def create_workspace(
    ws_in: ManagedWorkspaceCreate,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    return await service.create_workspace(ws_in)

@router.get("/workspaces", response_model=List[ManagedWorkspace], dependencies=[Depends(require_admin)])
async def list_workspaces(
    organization_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select
    from app.models.managed_control_plane import ManagedWorkspace
    
    stmt = select(ManagedWorkspace)
    if organization_id:
        stmt = stmt.where(ManagedWorkspace.organization_id == organization_id)
    
    result = await session.execute(stmt)
    return result.scalars().all()

# --- Appliances ---

@router.post("/appliances/enrollment-token", response_model=ApplianceEnrollmentToken, dependencies=[Depends(require_admin)])
async def create_enrollment_token(
    workspace_id: uuid.UUID,
    expires_in_hours: int = 24,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    enrollment = await service.generate_enrollment_token(workspace_id, expires_in_hours)
    return ApplianceEnrollmentToken(
        enrollment_token=enrollment.enrollment_token,
        expires_at=enrollment.expires_at
    )

@router.post("/appliances/enroll", response_model=ApplianceEnrollResponse)
async def enroll_appliance(
    enroll_in: ApplianceEnrollRequest,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    appliance = await service.enroll_appliance(enroll_in)
    
    if not appliance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired enrollment token"
        )
    
    return ApplianceEnrollResponse(
        appliance_id=appliance.id,
        workspace_id=appliance.workspace_id,
        config={
            "control_plane_url": str(settings.public_base_url),
            "heartbeat_interval_seconds": 60,
        }
    )

@router.post("/appliances/{appliance_id}/heartbeat")
async def record_heartbeat(
    appliance_id: uuid.UUID,
    payload: ApplianceHeartbeatPayload,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    success = await service.record_heartbeat(appliance_id, payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Appliance not found or revoked"
        )
    
    return {"status": "ok"}

@router.post("/appliances/{appliance_id}/revoke", dependencies=[Depends(require_admin)])
async def revoke_appliance(
    appliance_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    await service.revoke_appliance(appliance_id)
    return {"status": "revoked"}

@router.get("/appliances", response_model=List[ManagedAppliance], dependencies=[Depends(require_admin)])
async def list_appliances(
    workspace_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_db_session),
):
    service = ManagedControlPlaneService(session)
    return await service.list_appliances(workspace_id)
