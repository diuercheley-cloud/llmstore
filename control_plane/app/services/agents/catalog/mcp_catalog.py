import uuid

from app.models.agents.agent_catalog import MCPCatalogEntry
from sqlalchemy.ext.asyncio import AsyncSession


class MCPCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_mcp(self, catalog_entry_id: uuid.UUID, endpoint: str):
        mcp = MCPCatalogEntry(catalog_entry_id=catalog_entry_id, mcp_endpoint=endpoint)
        self.db.add(mcp)
        await self.db.commit()
        return mcp
