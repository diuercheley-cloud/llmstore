# Owner: agent-platform
import uuid
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentCatalogItem, AgentCatalogVersion, AgentCatalogRollback
from app.core.time import utc_now
from app.services.admin_rbac import record_admin_audit_event

logger = logging.getLogger(__name__)

class AgentCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _compute_checksum(self, configuration: Dict[str, Any]) -> str:
        serialized = json.dumps(configuration, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    async def register_item_version(
        self,
        item_type: str,
        name: str,
        version: str,
        configuration: Dict[str, Any],
        owner: str,
        compatibility: Optional[str] = "v1"
    ) -> AgentCatalogVersion:
        # Check if item exists, or create it
        res = await self.db.execute(
            select(AgentCatalogItem).where(
                AgentCatalogItem.item_type == item_type,
                AgentCatalogItem.name == name
            )
        )
        item = res.scalar_one_or_none()
        if not item:
            item = AgentCatalogItem(
                item_type=item_type,
                name=name,
                owner=owner,
                status="draft"
            )
            self.db.add(item)
            await self.db.flush()

        checksum = self._compute_checksum(configuration)

        # Check if this version already exists
        res_v = await self.db.execute(
            select(AgentCatalogVersion).where(
                AgentCatalogVersion.catalog_item_id == item.id,
                AgentCatalogVersion.version == version
            )
        )
        if res_v.scalar_one_or_none():
            raise ValueError(f"Version {version} for {item_type} {name} already exists.")

        cat_version = AgentCatalogVersion(
            catalog_item_id=item.id,
            version=version,
            checksum=checksum,
            configuration_json=configuration,
            compatibility=compatibility,
            created_at=utc_now()
        )
        self.db.add(cat_version)
        await self.db.commit()
        await self.db.refresh(cat_version)
        
        logger.info(f"Registered new {item_type} version: {name}@{version} (checksum: {checksum[:8]})")
        return cat_version

    async def list_items(self, item_type: Optional[str] = None) -> List[AgentCatalogItem]:
        query = select(AgentCatalogItem)
        if item_type:
            query = query.where(AgentCatalogItem.item_type == item_type)
        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def get_item_versions(self, item_id: uuid.UUID) -> List[AgentCatalogVersion]:
        res = await self.db.execute(
            select(AgentCatalogVersion)
            .where(AgentCatalogVersion.catalog_item_id == item_id)
            .order_by(AgentCatalogVersion.created_at.desc())
        )
        return list(res.scalars().all())

    async def promote_to_production(self, item_id: uuid.UUID, version_id: uuid.UUID, performed_by: str) -> AgentCatalogItem:
        item = await self.db.get(AgentCatalogItem, item_id)
        ver = await self.db.get(AgentCatalogVersion, version_id)
        
        if not item or not ver or ver.catalog_item_id != item.id:
            raise ValueError("Item or Version not found")

        # Promotion Gate Simulation (In real system, would check Evals)
        # For now, we just ensure it's not a generic 'draft' if we want stricter gates
        
        item.status = "production"
        item.updated_at = utc_now()
        ver.promoted_at = utc_now()

        await record_admin_audit_event(
            self.db,
            event_type="agent.catalog.promote",
            status="success",
            actor_identifier=performed_by,
            target_type="agent_catalog_item",
            target_id=str(item_id),
            metadata={"version": ver.version, "checksum": ver.checksum}
        )

        await self.db.commit()
        return item

    async def rollback(
        self, 
        item_id: uuid.UUID, 
        target_version_id: uuid.UUID, 
        performed_by: str, 
        reason: Optional[str] = None
    ) -> AgentCatalogRollback:
        item = await self.db.get(AgentCatalogItem, item_id)
        target_ver = await self.db.get(AgentCatalogVersion, target_version_id)

        if not item or not target_ver or target_ver.catalog_item_id != item.id:
            raise ValueError("Item or Target Version not found")

        # Find current production version
        res_curr = await self.db.execute(
            select(AgentCatalogVersion)
            .where(AgentCatalogVersion.catalog_item_id == item_id)
            .where(AgentCatalogVersion.promoted_at != None)
            .order_by(AgentCatalogVersion.promoted_at.desc())
            .limit(1)
        )
        current_ver = res_curr.scalar_one_or_none()

        rollback = AgentCatalogRollback(
            catalog_item_id=item_id,
            from_version_id=current_ver.id if current_ver else target_version_id, # If no prod, rollback from itself (dummy)
            to_version_id=target_version_id,
            reason=reason,
            performed_by=performed_by,
            created_at=utc_now()
        )
        self.db.add(rollback)

        # Effect: make target version the "active" one (promoted)
        target_ver.promoted_at = utc_now()
        item.updated_at = utc_now()

        await record_admin_audit_event(
            self.db,
            event_type="agent.catalog.rollback",
            status="success",
            actor_identifier=performed_by,
            target_type="agent_catalog_item",
            target_id=str(item_id),
            metadata={
                "from_version": current_ver.version if current_ver else "none",
                "to_version": target_ver.version,
                "reason": reason
            }
        )

        await self.db.commit()
        return rollback
