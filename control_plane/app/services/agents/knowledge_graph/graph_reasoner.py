# Owner: agent-platform
"""
GraphReasoner — thin wrapper around GraphRetriever for agent-facing reasoning.

Provides synchronous-looking find_path() for agent code that already has
an active event loop.  Use GraphRetriever directly for pure async code.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .graph_models import PathResult
from .graph_retriever import GraphRetriever


class GraphReasoner:
    """
    Agent-facing reasoning interface for graph pathfinding.

    Unlike the old stub (which returned [] with a TODO comment), this
    class delegates to the real BFS implementation in InternalSQLGraphProvider
    via GraphRetriever.
    """

    def __init__(self, db: AsyncSession):
        self._retriever = GraphRetriever(db)

    async def find_path(
        self,
        tenant_id: str,
        src_id: str,
        dst_id: str,
        relation_type: str | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> PathResult:
        """
        Real BFS shortest path from src_id to dst_id.

        Returns a PathResult with full metadata (nodes, edges, relation_types,
        provenance, confidence, traversal_cost, depth, query_time_ms).
        An empty path ONLY occurs when status != PathStatus.found.
        """
        return await self._retriever.find_path(
            tenant_id=tenant_id,
            source_entity_id=src_id,
            target_entity_id=dst_id,
            relation_type=relation_type,
            max_depth=max_depth,
            max_nodes=max_nodes,
            timeout_ms=timeout_ms,
        )
