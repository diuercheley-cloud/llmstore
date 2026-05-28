# Owner: agent-platform
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentMemoryItem


class SemanticMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, tenant_id: str, query: str, limit: int = 10) -> list[AgentMemoryItem]:
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.tenant_id == tenant_id,
            AgentMemoryItem.memory_type.in_(["semantic", "long_term"]),
            AgentMemoryItem.raw_content.ilike(f"%{query}%"),
        ).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())
