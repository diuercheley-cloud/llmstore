import uuid

from app.models.agents.agent_catalog import ConnectorCatalogEntry
from sqlalchemy.ext.asyncio import AsyncSession


class ConnectorCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_connector(
        self, catalog_entry_id: uuid.UUID, connector_type: str, credential_refs: dict
    ):
        connector = ConnectorCatalogEntry(
            catalog_entry_id=catalog_entry_id,
            connector_type=connector_type,
            credential_references=credential_refs,
        )
        self.db.add(connector)
        await self.db.commit()
        return connector
