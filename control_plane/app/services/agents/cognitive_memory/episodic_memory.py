# Owner: agent-platform
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentMemoryItem


class EpisodicMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, tenant_id: str, agent_id=None) -> list[AgentMemoryItem]:
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.tenant_id == tenant_id,
            AgentMemoryItem.memory_type == "episodic",
        )
        if agent_id is not None:
            stmt = stmt.where(AgentMemoryItem.agent_id == agent_id)
        return list((await self.db.execute(stmt)).scalars().all())
