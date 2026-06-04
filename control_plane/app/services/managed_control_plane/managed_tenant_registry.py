import logging
import uuid
from typing import List, Optional

from app.models.managed_control_plane import ManagedAppliance, ManagedOrganization, ManagedWorkspace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ManagedTenantRegistry:
    """
    Registry for managing tenants (organizations, workspaces, appliances)
    in the managed control plane topology.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_organization(self, name: str, slug: str) -> ManagedOrganization:
        org = ManagedOrganization(name=name, slug=slug)
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        logger.info(f"Created organization {org.id} ({slug})")
        return org

    async def get_organization(self, org_id: uuid.UUID) -> Optional[ManagedOrganization]:
        return await self.db.get(ManagedOrganization, org_id)

    async def get_organization_by_slug(self, slug: str) -> Optional[ManagedOrganization]:
        stmt = select(ManagedOrganization).where(ManagedOrganization.slug == slug)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_organizations(self) -> List[ManagedOrganization]:
        stmt = select(ManagedOrganization).order_by(ManagedOrganization.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def suspend_organization(self, org_id: uuid.UUID) -> Optional[ManagedOrganization]:
        org = await self.get_organization(org_id)
        if not org:
            return None
        org.status = "suspended"
        await self.db.flush()
        logger.info(f"Suspended organization {org_id}")
        return org

    async def create_workspace(self, organization_id: uuid.UUID, name: str, slug: str) -> ManagedWorkspace:
        ws = ManagedWorkspace(organization_id=organization_id, name=name, slug=slug)
        self.db.add(ws)
        await self.db.flush()
        await self.db.refresh(ws)
        logger.info(f"Created workspace {ws.id} ({slug}) in org {organization_id}")
        return ws

    async def list_workspaces(self, organization_id: uuid.UUID) -> List[ManagedWorkspace]:
        stmt = select(ManagedWorkspace).where(
            ManagedWorkspace.organization_id == organization_id
        ).order_by(ManagedWorkspace.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def register_appliance(
        self, workspace_id: uuid.UUID, appliance_external_id: str, name: str
    ) -> ManagedAppliance:
        appliance = ManagedAppliance(
            workspace_id=workspace_id,
            appliance_external_id=appliance_external_id,
            name=name,
        )
        self.db.add(appliance)
        await self.db.flush()
        await self.db.refresh(appliance)
        logger.info(f"Registered appliance {appliance.id} ({appliance_external_id})")
        return appliance

    async def get_appliance_by_external_id(self, external_id: str) -> Optional[ManagedAppliance]:
        stmt = select(ManagedAppliance).where(
            ManagedAppliance.appliance_external_id == external_id
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_appliances(self, workspace_id: uuid.UUID) -> List[ManagedAppliance]:
        stmt = select(ManagedAppliance).where(
            ManagedAppliance.workspace_id == workspace_id
        ).order_by(ManagedAppliance.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
