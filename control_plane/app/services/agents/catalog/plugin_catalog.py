import uuid

from app.models.agent_catalog import PluginCatalogEntry
from sqlalchemy.ext.asyncio import AsyncSession


class PluginCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_plugin(self, catalog_entry_id: uuid.UUID, runtime_type: str, checksum: str, is_signed: bool = False):
        plugin = PluginCatalogEntry(
            catalog_entry_id=catalog_entry_id,
            runtime_type=runtime_type,
            checksum_sha256=checksum,
            is_signed=is_signed
        )
        self.db.add(plugin)
        await self.db.commit()
        return plugin
