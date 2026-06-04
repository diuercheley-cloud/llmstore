# Owner: agent-platform
from datetime import timedelta

from app.core.time import utc_now
from app.models.agents import AgentMemoryItem
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class WorkingMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def active(self, tenant_id: str, agent_id, ttl_seconds: int = 3600) -> list[AgentMemoryItem]:
        threshold = utc_now() - timedelta(seconds=ttl_seconds)
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.tenant_id == tenant_id,
            AgentMemoryItem.agent_id == agent_id,
            AgentMemoryItem.memory_type == "working",
            AgentMemoryItem.created_at >= threshold,
        )
        return list((await self.db.execute(stmt)).scalars().all())
