import uuid
from typing import List, Optional

from app.models.agents.agent_catalog import AgentCapabilityCatalogEntry, CapabilityApprovalEvent
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class CapabilityCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_entries(self, category: Optional[str] = None) -> List[AgentCapabilityCatalogEntry]:
        query = select(AgentCapabilityCatalogEntry)
        if category:
            query = query.where(AgentCapabilityCatalogEntry.category == category)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def install_entry(self, entry_data: dict) -> AgentCapabilityCatalogEntry:
        entry = AgentCapabilityCatalogEntry(**entry_data)
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def approve_entry(self, entry_id: uuid.UUID, approver_id: uuid.UUID, comment: str = None):
        result = await self.db.execute(select(AgentCapabilityCatalogEntry).where(AgentCapabilityCatalogEntry.id == entry_id))
        entry = result.scalars().first()
        if not entry:
             raise ValueError("Entry not found")
        
        event = CapabilityApprovalEvent(
            catalog_entry_id=entry_id,
            approver_id=approver_id,
            previous_status=entry.status,
            new_status="approved",
            comment=comment
        )
        entry.status = "approved"
        self.db.add(event)
        await self.db.commit()
        return entry

    async def disable_entry(self, entry_id: uuid.UUID):
        await self.db.execute(
            update(AgentCapabilityCatalogEntry)
            .where(AgentCapabilityCatalogEntry.id == entry_id)
            .values(status="disabled")
        )
        await self.db.commit()
