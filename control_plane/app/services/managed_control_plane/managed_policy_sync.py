import logging
import uuid
from typing import List, Optional

from app.core.time import utc_now
from app.models.managed_control_plane import (
    ManagedControlPlaneLink,
    ManagedPolicySyncEvent,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ManagedPolicySync:
    """
    Synchronizes policies across managed control plane links.
    Handles push, pull, and event tracking for policy propagation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def push_policies(
        self,
        link_id: uuid.UUID,
        policy_type: str,
        policies: dict,
    ) -> ManagedPolicySyncEvent:
        link = await self.db.get(ManagedControlPlaneLink, link_id)
        if not link:
            raise ValueError(f"Control plane link {link_id} not found")

        event = ManagedPolicySyncEvent(
            link_id=link_id,
            policy_type=policy_type,
            status="synced",
            details={"policies_count": len(policies), "policies": policies},
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        logger.info(f"Pushed {policy_type} policies to link {link_id}")
        return event

    async def pull_policies(
        self,
        link_id: uuid.UUID,
        policy_type: str,
    ) -> Optional[dict]:
        link = await self.db.get(ManagedControlPlaneLink, link_id)
        if not link:
            raise ValueError(f"Control plane link {link_id} not found")

        stmt = select(ManagedPolicySyncEvent).where(
            ManagedPolicySyncEvent.link_id == link_id,
            ManagedPolicySyncEvent.policy_type == policy_type,
            ManagedPolicySyncEvent.status == "synced",
        ).order_by(ManagedPolicySyncEvent.created_at.desc()).limit(1)
        res = await self.db.execute(stmt)
        last_event = res.scalar_one_or_none()
        if not last_event:
            return None
        return (last_event.details or {}).get("policies")

    async def get_sync_history(
        self, link_id: uuid.UUID, limit: int = 50
    ) -> List[ManagedPolicySyncEvent]:
        stmt = select(ManagedPolicySyncEvent).where(
            ManagedPolicySyncEvent.link_id == link_id
        ).order_by(ManagedPolicySyncEvent.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def register_link(
        self, upstream_url: str, sync_policies: bool = True
    ) -> ManagedControlPlaneLink:
        link = ManagedControlPlaneLink(
            upstream_url=upstream_url,
            sync_policies=sync_policies,
        )
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        logger.info(f"Registered control plane link {link.id} -> {upstream_url}")
        return link

    async def update_link_status(self, link_id: uuid.UUID, status: str) -> Optional[ManagedControlPlaneLink]:
        link = await self.db.get(ManagedControlPlaneLink, link_id)
        if not link:
            return None
        link.status = status
        link.last_heartbeat_at = utc_now()
        await self.db.flush()
        return link

    async def list_links(self) -> List[ManagedControlPlaneLink]:
        stmt = select(ManagedControlPlaneLink).order_by(
            ManagedControlPlaneLink.created_at.desc()
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
