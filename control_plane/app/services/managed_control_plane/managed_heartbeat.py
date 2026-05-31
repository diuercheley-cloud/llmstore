import asyncio
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.managed_control_plane import (
    ManagedAppliance,
    ApplianceHeartbeat,
    ManagedControlPlaneLink,
)
from app.core.time import utc_now

logger = logging.getLogger(__name__)


class ManagedHeartbeatService:
    """
    Processes heartbeats from managed appliances and control plane links.
    Tracks health status, readiness, and capacity.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_appliance_heartbeat(
        self,
        appliance_external_id: str,
        version: str,
        health_status: str,
        readiness: bool,
        capacity_summary: Optional[dict] = None,
        enabled_providers: Optional[list] = None,
        available_models: Optional[list] = None,
    ) -> Optional[ManagedAppliance]:
        stmt = select(ManagedAppliance).where(
            ManagedAppliance.appliance_external_id == appliance_external_id
        )
        res = await self.db.execute(stmt)
        appliance = res.scalar_one_or_none()
        if not appliance:
            logger.warning(f"Heartbeat from unknown appliance: {appliance_external_id}")
            return None

        appliance.version = version
        appliance.health_status = health_status
        appliance.readiness = readiness
        appliance.last_heartbeat_at = utc_now()
        if capacity_summary:
            appliance.capacity_summary = capacity_summary
        if enabled_providers:
            appliance.enabled_providers = enabled_providers
        if available_models:
            appliance.available_models = available_models

        heartbeat = ApplianceHeartbeat(
            appliance_id=appliance.id,
            version=version,
            health_status=health_status,
            readiness=readiness,
            capacity_summary=capacity_summary or {},
            enabled_providers=enabled_providers or [],
            available_models=available_models or [],
        )
        self.db.add(heartbeat)
        await self.db.flush()

        logger.info(
            f"Processed heartbeat for appliance {appliance_external_id}: "
            f"health={health_status}, ready={readiness}"
        )
        return appliance

    async def process_link_heartbeat(self, link_id: uuid.UUID) -> Optional[ManagedControlPlaneLink]:
        link = await self.db.get(ManagedControlPlaneLink, link_id)
        if not link:
            logger.warning(f"Heartbeat from unknown control plane link: {link_id}")
            return None

        link.status = "connected"
        link.last_heartbeat_at = utc_now()
        await self.db.flush()
        logger.info(f"Processed heartbeat for control plane link {link_id}")
        return link

    async def check_stale_appliances(
        self, timeout_minutes: int = 15
    ) -> int:
        deadline = utc_now() - timedelta(minutes=timeout_minutes)
        stmt = select(ManagedAppliance).where(
            ManagedAppliance.last_heartbeat_at < deadline,
            ManagedAppliance.status.in_(["enrolled", "online"]),
        )
        res = await self.db.execute(stmt)
        stale = list(res.scalars().all())

        for appliance in stale:
            appliance.status = "offline"
            appliance.health_status = "critical"
            logger.warning(
                f"Appliance {appliance.appliance_external_id} ({appliance.id}) "
                f"marked offline — no heartbeat for {timeout_minutes}+ minutes"
            )
        await self.db.flush()
        return len(stale)

    async def check_stale_links(self, timeout_minutes: int = 15) -> int:
        deadline = utc_now() - timedelta(minutes=timeout_minutes)
        stmt = select(ManagedControlPlaneLink).where(
            ManagedControlPlaneLink.last_heartbeat_at < deadline,
            ManagedControlPlaneLink.status == "connected",
        )
        res = await self.db.execute(stmt)
        stale = list(res.scalars().all())

        for link in stale:
            link.status = "disconnected"
            logger.warning(
                f"Control plane link {link.id} ({link.upstream_url}) "
                f"disconnected — no heartbeat for {timeout_minutes}+ minutes"
            )
        await self.db.flush()
        return len(stale)

    async def get_appliance_heartbeat_history(
        self, appliance_id: uuid.UUID, limit: int = 50
    ):
        stmt = select(ApplianceHeartbeat).where(
            ApplianceHeartbeat.appliance_id == appliance_id
        ).order_by(ApplianceHeartbeat.timestamp.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
