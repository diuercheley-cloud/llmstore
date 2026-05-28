from sqlalchemy.ext.asyncio import AsyncSession

from .graph_models import GraphQueryRequest, GraphQueryResult
from .graph_store import GraphStore


class GraphRetriever:
    def __init__(self, db: AsyncSession):
        self.store = GraphStore(db)

    async def get_entity_relations(self, tenant_id: str, entity_id: str) -> GraphQueryResult:
        return await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="neighborhood",
                entity_id=entity_id,
            )
        )
