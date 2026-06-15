# Owner: agent-platform
"""
GraphRetriever — high-level retrieval API for the Knowledge Graph.

Exposes:
  - get_entity_relations: 1-hop neighbourhood
  - find_path: BFS shortest path between two entities
  - get_subgraph: bounded BFS subgraph from a starting entity
  - get_dependencies: directed dependency traversal
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .graph_models import GraphQueryRequest, GraphQueryResult, PathResult
from .graph_store import GraphStore


class GraphRetriever:
    def __init__(self, db: AsyncSession):
        self.store = GraphStore(db)

    async def get_entity_relations(self, tenant_id: str, entity_id: str) -> GraphQueryResult:
        """1-hop neighbourhood of an entity."""
        return await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="neighborhood",
                entity_id=entity_id,
            )
        )

    async def find_path(
        self,
        tenant_id: str,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> PathResult:
        """
        BFS shortest path from source to target within the same tenant.

        Returns a PathResult with status, nodes, edges, relation_types,
        provenance, confidence, traversal_cost, depth, and query_time_ms.

        Empty path only occurs when:
          - status == no_path (no route exists in the graph)
          - status == timeout (search exceeded timeout_ms)
          - status == capability_not_supported (provider lacks pathfinding)
          - status == mock (AGENT_KG_MOCK_MODE=true)
        """
        result = await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="path",
                entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relation_type=relation_type,
                max_depth=max_depth,
                max_nodes=max_nodes,
                timeout_ms=timeout_ms,
            )
        )
        # path is always populated for query_type="path"
        return result.path  # type: ignore[return-value]

    async def get_dependencies(
        self,
        tenant_id: str,
        entity_id: str,
        relation_type: str | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> PathResult:
        """Directed dependency traversal from an entity outward."""
        result = await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="dependencies",
                entity_id=entity_id,
                relation_type=relation_type,
                max_depth=max_depth,
                max_nodes=max_nodes,
                timeout_ms=timeout_ms,
            )
        )
        return result.path  # type: ignore[return-value]

    async def get_subgraph(
        self,
        tenant_id: str,
        entity_id: str,
        max_depth: int = 3,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> GraphQueryResult:
        """Bounded BFS subgraph starting from entity_id."""
        return await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="neighborhood",
                entity_id=entity_id,
                max_depth=max_depth,
                max_nodes=max_nodes,
                timeout_ms=timeout_ms,
            )
        )
