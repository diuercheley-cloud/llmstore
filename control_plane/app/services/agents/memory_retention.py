"""
Owner: agent-platform
Status: beta
"""
import uuid
from typing import Optional

from app.core.time import utc_now
from app.models.agents.agents import AgentMemoryDeleteRequest, AgentMemoryItem
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class MemoryRetentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_retention(self) -> dict:
        stmt = select(AgentMemoryItem).where(AgentMemoryItem.retention_until <= utc_now())
        res = await self.db.execute(stmt)
        items = res.scalars().all()
        deleted = 0
        for item in items:
            await self.db.delete(item)
            deleted += 1
        await self.db.commit()
        return {"items_deleted": deleted}

    async def process_delete_requests(self) -> dict:
        stmt = select(AgentMemoryDeleteRequest).where(AgentMemoryDeleteRequest.status == "pending")
        res = await self.db.execute(stmt)
        requests = res.scalars().all()
        
        total_deleted = 0
        for req in requests:
            # find items to delete
            item_stmt = select(AgentMemoryItem).where(AgentMemoryItem.tenant_id == req.tenant_id)
            if req.agent_id:
                item_stmt = item_stmt.where(AgentMemoryItem.agent_id == req.agent_id)
            if req.memory_type:
                item_stmt = item_stmt.where(AgentMemoryItem.memory_type == req.memory_type)
                
            items_res = await self.db.execute(item_stmt)
            items = items_res.scalars().all()
            for i in items:
                await self.db.delete(i)
                total_deleted += 1
                
            req.status = "completed"
            req.items_deleted = len(items)
            req.completed_at = utc_now()
            
        await self.db.commit()
        return {"requests_processed": len(requests), "items_deleted": total_deleted}

    async def create_delete_request(self, tenant_id: str, agent_id: Optional[uuid.UUID] = None, memory_type: Optional[str] = None) -> AgentMemoryDeleteRequest:
        req = AgentMemoryDeleteRequest(
            tenant_id=tenant_id,
            agent_id=agent_id,
            memory_type=memory_type
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return req
