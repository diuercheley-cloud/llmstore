import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.managed_control_plane import (
    ManagedOrganization,
    ManagedWorkspace,
    ManagedAppliance,
    ApplianceEnrollment,
    ApplianceHeartbeat,
)
from app.services.managed_metrics import managed_appliance_heartbeats_total
from app.schemas.managed_control_plane import (
    ManagedOrganizationCreate,
    ManagedWorkspaceCreate,
    ApplianceEnrollRequest,
    ApplianceHeartbeatPayload,
)

logger = logging.getLogger(__name__)

class ManagedControlPlaneService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_organization(self, org_in: ManagedOrganizationCreate) -> ManagedOrganization:
        db_org = ManagedOrganization(
            name=org_in.name,
            slug=org_in.slug,
        )
        self.session.add(db_org)
        await self.session.commit()
        await self.session.refresh(db_org)
        return db_org

    async def create_workspace(self, ws_in: ManagedWorkspaceCreate) -> ManagedWorkspace:
        db_ws = ManagedWorkspace(
            organization_id=ws_in.organization_id,
            name=ws_in.name,
            slug=ws_in.slug,
        )
        self.session.add(db_ws)
        await self.session.commit()
        await self.session.refresh(db_ws)
        return db_ws

    async def generate_enrollment_token(self, workspace_id: uuid.UUID, expires_in_hours: int = 24) -> ApplianceEnrollment:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        db_enrollment = ApplianceEnrollment(
            workspace_id=workspace_id,
            enrollment_token=token,
            expires_at=expires_at,
        )
        self.session.add(db_enrollment)
        await self.session.commit()
        await self.session.refresh(db_enrollment)
        return db_enrollment

    async def enroll_appliance(self, enroll_in: ApplianceEnrollRequest) -> Optional[ManagedAppliance]:
        # 1. Validate token
        stmt = select(ApplianceEnrollment).where(
            ApplianceEnrollment.enrollment_token == enroll_in.enrollment_token,
            ApplianceEnrollment.is_used == False,
            ApplianceEnrollment.expires_at > datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        enrollment = result.scalar_one_or_none()
        
        if not enrollment:
            logger.warning(f"Invalid or expired enrollment token: {enroll_in.enrollment_token}")
            return None
        
        # 2. Create appliance
        db_appliance = ManagedAppliance(
            workspace_id=enrollment.workspace_id,
            appliance_external_id=enroll_in.appliance_external_id,
            name=enroll_in.name,
            status="enrolled",
        )
        self.session.add(db_appliance)
        await self.session.flush() # Get ID
        
        # 3. Mark token as used
        enrollment.is_used = True
        enrollment.used_at = datetime.utcnow()
        enrollment.used_by_appliance_id = db_appliance.id
        
        await self.session.commit()
        await self.session.refresh(db_appliance)
        return db_appliance

    async def record_heartbeat(self, appliance_id: uuid.UUID, payload: ApplianceHeartbeatPayload) -> bool:
        # 1. Check if appliance exists and is not revoked
        stmt = select(ManagedAppliance).where(ManagedAppliance.id == appliance_id)
        result = await self.session.execute(stmt)
        appliance = result.scalar_one_or_none()
        
        if not appliance or appliance.status == "revoked":
            return False
        
        # 2. Record heartbeat history
        db_heartbeat = ApplianceHeartbeat(
            appliance_id=appliance_id,
            version=payload.version,
            health_status=payload.health_status,
            readiness=payload.readiness,
            capacity_summary=payload.capacity_summary,
            enabled_providers=payload.enabled_providers,
            available_models=payload.available_models,
        )
        self.session.add(db_heartbeat)
        
        # 3. Update appliance current status
        appliance.status = "online"
        appliance.version = payload.version
        appliance.health_status = payload.health_status
        appliance.readiness = payload.readiness
        appliance.last_heartbeat_at = datetime.utcnow()
        appliance.capacity_summary = payload.capacity_summary
        appliance.enabled_providers = payload.enabled_providers
        appliance.available_models = payload.available_models
        
        # 4. Update metrics
        managed_appliance_heartbeats_total.labels(appliance_id=str(appliance_id)).inc()
        
        await self.session.commit()
        return True

    async def revoke_appliance(self, appliance_id: uuid.UUID) -> bool:
        stmt = update(ManagedAppliance).where(ManagedAppliance.id == appliance_id).values(status="revoked", updated_at=datetime.utcnow())
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def list_appliances(self, workspace_id: Optional[uuid.UUID] = None) -> List[ManagedAppliance]:
        stmt = select(ManagedAppliance)
        if workspace_id:
            stmt = stmt.where(ManagedAppliance.workspace_id == workspace_id)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_organization(self, org_id: uuid.UUID) -> Optional[ManagedOrganization]:
        stmt = select(ManagedOrganization).where(ManagedOrganization.id == org_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_workspace(self, workspace_id: uuid.UUID) -> Optional[ManagedWorkspace]:
        stmt = select(ManagedWorkspace).where(ManagedWorkspace.id == workspace_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
