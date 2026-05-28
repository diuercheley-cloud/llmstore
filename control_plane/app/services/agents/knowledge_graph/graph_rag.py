from sqlalchemy.ext.asyncio import AsyncSession

from .graph_models import GraphQueryRequest, GraphQueryResult
from .graph_store import GraphStore


class GraphRAG:
    def __init__(self, db: AsyncSession):
        self.store = GraphStore(db)

    async def query(self, tenant_id: str, text: str, limit: int = 10) -> GraphQueryResult:
        result = await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="entity_search",
                text=text,
                entity_name=text,
                limit=limit,
            )
        )
        entity_names = ", ".join(entity.name for entity in result.entities) or "No entities found"
        result.context_block = (
            f"Vector Result: {text}\n"
            f"Graph Result: {entity_names}\n"
            f"Provenance: {', '.join((item.get('source_id') or 'inline') for item in result.provenance) or 'n/a'}"
        )
        return result
