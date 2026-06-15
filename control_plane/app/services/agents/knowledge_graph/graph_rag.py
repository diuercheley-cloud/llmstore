# Owner: agent-platform
"""
GraphRAG — Graph-augmented Retrieval for LLM context injection.

Combines vector-like entity search with pathfinding to build a rich
context_block that includes:
  - matched entities
  - the shortest path between key entities when two are identified
  - full provenance per node/edge for citation
  - confidence and traversal cost for the LLM to assess reliability

Usage:
    rag = GraphRAG(db)
    result = await rag.query(tenant_id, "How does ProjectA depend on ServiceB?")
    # result.context_block contains a structured, citation-ready string
    # result.path contains the PathResult with full metadata
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .graph_models import GraphQueryRequest, GraphQueryResult, PathResult, PathStatus
from .graph_store import GraphStore


class GraphRAG:
    def __init__(self, db: AsyncSession):
        self.store = GraphStore(db)

    async def query(self, tenant_id: str, text: str, limit: int = 10) -> GraphQueryResult:
        """
        Entity search augmented with provenance.

        Returns a GraphQueryResult with:
          - entities: matched entities
          - context_block: formatted string for LLM prompt injection
          - provenance: per-entity source references
        """
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
        provenance_refs = (
            ", ".join((item.get("source_id") or "inline") for item in result.provenance) or "n/a"
        )
        result.context_block = (
            f"Vector Result: {text}\nGraph Result: {entity_names}\nProvenance: {provenance_refs}"
        )
        return result

    async def query_with_path(
        self,
        tenant_id: str,
        text: str,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
        limit: int = 10,
    ) -> GraphQueryResult:
        """
        Entity search + graph path injection for LLM context.

        Finds the shortest path between source and target entities and injects
        a rich context block with:
          - path nodes and edge labels
          - provenance per node
          - confidence score
          - traversal cost and depth

        When no path exists, the context block explains why (no_path /
        timeout / capability_not_supported) so the LLM can reason about it
        explicitly rather than receiving a silent empty result.
        """
        # Run entity search for ambient context
        entity_result = await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="entity_search",
                text=text,
                entity_name=text,
                limit=limit,
            )
        )

        # Run pathfinding
        path_result_wrapper = await self.store.query(
            GraphQueryRequest(
                tenant_id=tenant_id,
                query_type="path",
                entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relation_type=relation_type,
                max_depth=max_depth,
                max_nodes=max_nodes,
                timeout_ms=timeout_ms,
                limit=limit,
            )
        )
        path: PathResult = path_result_wrapper.path  # type: ignore[assignment]

        # Build context block
        entity_names = ", ".join(e.name for e in entity_result.entities) or "No entities found"
        provenance_refs = (
            ", ".join((item.get("source_id") or "inline") for item in entity_result.provenance)
            or "n/a"
        )

        if path.status == PathStatus.found:
            path_desc = " → ".join(n.name for n in path.nodes)
            edge_types = ", ".join(path.relation_types) or "unknown"
            path_provenance = (
                "; ".join(
                    f"{p['entity_id']}={p.get('source_id') or 'inline'}" for p in path.provenance
                )
                or "n/a"
            )
            path_block = (
                f"Path ({path.depth} hops, cost={path.traversal_cost}, "
                f"confidence={path.confidence:.2f}, time={path.query_time_ms:.1f}ms): "
                f"{path_desc} [{edge_types}]\n"
                f"Path Provenance: {path_provenance}"
            )
        else:
            path_block = f"Path not available: status={path.status.value}" + (
                f", reason={path.reason}" if path.reason else ""
            )

        context_block = (
            f"Vector Result: {text}\n"
            f"Graph Result: {entity_names}\n"
            f"Provenance: {provenance_refs}\n"
            f"{path_block}"
        )

        return GraphQueryResult(
            entities=entity_result.entities,
            relations=path.edges,
            context_block=context_block,
            provenance=entity_result.provenance + path.provenance,
            path=path,
        )
