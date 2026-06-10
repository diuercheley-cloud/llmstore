# Owner: agent-platform
"""
InternalSQLGraphProvider — production SQL-backed knowledge graph provider.

Pathfinding is implemented as an async BFS executed entirely in Python
over SQL-fetched adjacency lists.  Each hop issues at most one SQL query
(fetching all relations for the current frontier in a single IN-clause),
so the total number of round-trips is bounded by max_depth.

Capabilities:
  - shortest_path (BFS, undirected or directed)
  - bounded_bfs   (returns subgraph up to max_depth / max_nodes)
  - neighborhood_traversal (1-hop neighbour set)
  - dependency_traversal (directed DFS for dependency chains)
  - relation_filter (include only specified relation types)
  - tenant isolation enforced at every SQL query
  - optional timeout via asyncio

Feature flags:
  AGENT_KG_MOCK_MODE          — allows mock returns (test/staging only)
  AGENT_KG_PATHFINDING_MAX_DEPTH
  AGENT_KG_PATHFINDING_MAX_NODES
  AGENT_KG_PATHFINDING_TIMEOUT_MS
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any

from app.models.agents.agent_knowledge_graph import (
    AgentKGEntity,
    AgentKGExtractionRun,
    AgentKGQueryEvent,
    AgentKGRelation,
    AgentKGSource,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


from .base import GraphProvider


class InternalSQLGraphProvider:
    """
    SQL-backed graph provider with real BFS/DFS pathfinding.
    
    Implements GraphProvider protocol.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Source / extraction lifecycle
    # ------------------------------------------------------------------

    async def create_source(self, tenant_id: str, uri: str, content_hash: str | None = None) -> AgentKGSource:
        source = AgentKGSource(tenant_id=tenant_id, uri=uri, content_hash=content_hash)
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def create_extraction_run(self, tenant_id: str, document_id: str | None = None) -> AgentKGExtractionRun:
        run = AgentKGExtractionRun(tenant_id=tenant_id, status="completed", document_id=document_id)
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    async def upsert_entity(
        self,
        tenant_id: str,
        name: str,
        entity_type: str,
        source_id: uuid.UUID | None = None,
        provenance: dict[str, Any] | None = None,
        confidence: float = 1.0,
        freshness: str = "fresh",
    ) -> AgentKGEntity:
        stmt = select(AgentKGEntity).where(
            AgentKGEntity.tenant_id == tenant_id,
            AgentKGEntity.name == name,
            AgentKGEntity.type == entity_type,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        metadata = {
            "source_id": str(source_id) if source_id else None,
            "provenance": provenance or {},
            "confidence": confidence,
            "freshness": freshness,
        }
        if existing:
            existing.metadata_ = metadata
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        entity = AgentKGEntity(
            tenant_id=tenant_id,
            name=name,
            type=entity_type,
            metadata_=metadata,
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def create_relation(
        self,
        tenant_id: str,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relation_type: str,
        provenance: str,
        source_id: uuid.UUID | None = None,
        confidence: float = 1.0,
        freshness: str = "fresh",
    ) -> AgentKGRelation:
        relation = AgentKGRelation(
            tenant_id=tenant_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
            source_provenance=provenance,
        )
        relation.__dict__["metadata"] = {
            "source_id": str(source_id) if source_id else None,
            "confidence": confidence,
            "freshness": freshness,
        }
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation

    # ------------------------------------------------------------------
    # Entity / relation listings
    # ------------------------------------------------------------------

    async def list_entities(self, tenant_id: str, entity_name: str | None = None) -> list[AgentKGEntity]:
        stmt = select(AgentKGEntity).where(AgentKGEntity.tenant_id == tenant_id)
        if entity_name:
            stmt = stmt.where(AgentKGEntity.name.ilike(f"%{entity_name}%"))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_relations(self, tenant_id: str, entity_id: uuid.UUID | None = None) -> list[AgentKGRelation]:
        stmt = select(AgentKGRelation).where(AgentKGRelation.tenant_id == tenant_id)
        if entity_id:
            stmt = stmt.where(
                or_(
                    AgentKGRelation.source_entity_id == entity_id,
                    AgentKGRelation.target_entity_id == entity_id,
                )
            )
        return list((await self.db.execute(stmt)).scalars().all())

    async def related_entities(self, tenant_id: str, entity_id: uuid.UUID) -> tuple[list[AgentKGEntity], list[AgentKGRelation]]:
        relations = await self.list_relations(tenant_id, entity_id=entity_id)
        entity_ids = {entity_id}
        entity_ids.update(relation.source_entity_id for relation in relations)
        entity_ids.update(relation.target_entity_id for relation in relations)
        stmt = select(AgentKGEntity).where(AgentKGEntity.tenant_id == tenant_id, AgentKGEntity.id.in_(entity_ids))
        entities = list((await self.db.execute(stmt)).scalars().all())
        return entities, relations

    # ------------------------------------------------------------------
    # Low-level adjacency helper (tenant-isolated, relation-filtered)
    # ------------------------------------------------------------------

    async def _fetch_relations_for_nodes(
        self,
        tenant_id: str,
        node_ids: set[uuid.UUID],
        relation_types: list[str] | None = None,
        directed: bool = False,
    ) -> list[AgentKGRelation]:
        """
        Fetch all relations incident to *node_ids* in a single SQL query.

        - tenant_id isolation: WHERE tenant_id = :tid always applied.
        - relation_types: if provided, filter to those types.
        - directed=False (default): fetch both outgoing and incoming edges.
        - directed=True: fetch only outgoing edges (source_entity_id IN node_ids).
        """
        if not node_ids:
            return []
        if directed:
            condition = AgentKGRelation.source_entity_id.in_(node_ids)
        else:
            condition = or_(
                AgentKGRelation.source_entity_id.in_(node_ids),
                AgentKGRelation.target_entity_id.in_(node_ids),
            )
        stmt = select(AgentKGRelation).where(
            AgentKGRelation.tenant_id == tenant_id,
            condition,
        )
        if relation_types:
            stmt = stmt.where(AgentKGRelation.relation_type.in_(relation_types))
        return list((await self.db.execute(stmt)).scalars().all())

    async def _fetch_entities_by_ids(self, tenant_id: str, entity_ids: set[uuid.UUID]) -> dict[uuid.UUID, AgentKGEntity]:
        if not entity_ids:
            return {}
        stmt = select(AgentKGEntity).where(
            AgentKGEntity.tenant_id == tenant_id,
            AgentKGEntity.id.in_(entity_ids),
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {r.id: r for r in rows}

    # ------------------------------------------------------------------
    # BFS shortest-path (undirected, relation-filtered, bounded)
    # ------------------------------------------------------------------

    async def shortest_path(
        self,
        tenant_id: str,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        relation_types: list[str] | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> tuple[list[AgentKGEntity], list[AgentKGRelation], dict[str, Any]]:
        """
        BFS shortest path between two entities within the same tenant.

        Returns (path_entities, path_relations, meta) where meta contains:
          - status: "found" | "no_path" | "timeout"
          - depth: hops in the path
          - traversal_cost: total edges examined
          - query_time_ms

        Tenant isolation: all queries include tenant_id = :tid.
        Cross-tenant access cannot occur because entity UUIDs from other
        tenants will never appear in a tenant-scoped adjacency query.
        """
        started = time.monotonic()
        deadline = started + timeout_ms / 1000.0

        if source_id == target_id:
            entity_map = await self._fetch_entities_by_ids(tenant_id, {source_id})
            entity = entity_map.get(source_id)
            elapsed_ms = (time.monotonic() - started) * 1000
            if entity:
                return (
                    [entity],
                    [],
                    {"status": "found", "depth": 0, "traversal_cost": 0, "query_time_ms": elapsed_ms},
                )
            return ([], [], {"status": "no_path", "depth": 0, "traversal_cost": 0, "query_time_ms": elapsed_ms})

        # BFS state
        # parent_edge[node_id] = (parent_id, relation) — used to reconstruct path
        parent_edge: dict[uuid.UUID, tuple[uuid.UUID, AgentKGRelation | None]] = {source_id: (source_id, None)}
        frontier: deque[uuid.UUID] = deque([source_id])
        visited: set[uuid.UUID] = {source_id}
        traversal_cost = 0
        found = False

        for depth in range(1, max_depth + 1):
            if not frontier:
                break
            if time.monotonic() > deadline:
                elapsed_ms = (time.monotonic() - started) * 1000
                return ([], [], {"status": "timeout", "depth": depth, "traversal_cost": traversal_cost, "query_time_ms": elapsed_ms})

            # Fetch all edges incident to the current frontier in one query
            frontier_set = set(frontier)
            frontier.clear()
            relations = await self._fetch_relations_for_nodes(tenant_id, frontier_set, relation_types, directed=False)
            traversal_cost += len(relations)

            for rel in relations:
                # Determine the neighbour node from this edge
                if rel.source_entity_id in frontier_set:
                    neighbour = rel.target_entity_id
                    parent = rel.source_entity_id
                else:
                    neighbour = rel.source_entity_id
                    parent = rel.target_entity_id

                if neighbour in visited:
                    continue
                visited.add(neighbour)
                parent_edge[neighbour] = (parent, rel)

                if len(visited) >= max_nodes:
                    # Node budget exhausted — treat as no-path (path may exist deeper)
                    elapsed_ms = (time.monotonic() - started) * 1000
                    return ([], [], {"status": "no_path", "depth": depth, "traversal_cost": traversal_cost, "query_time_ms": elapsed_ms})

                if neighbour == target_id:
                    found = True
                    break
                frontier.append(neighbour)

            if found:
                break

        elapsed_ms = (time.monotonic() - started) * 1000

        if not found:
            return ([], [], {"status": "no_path", "depth": 0, "traversal_cost": traversal_cost, "query_time_ms": elapsed_ms})

        # Reconstruct path from target back to source
        path_node_ids: list[uuid.UUID] = []
        path_relations: list[AgentKGRelation] = []
        cur = target_id
        while cur != source_id:
            path_node_ids.append(cur)
            parent, rel = parent_edge[cur]
            if rel is not None:
                path_relations.append(rel)
            cur = parent
        path_node_ids.append(source_id)
        path_node_ids.reverse()
        path_relations.reverse()

        entity_map = await self._fetch_entities_by_ids(tenant_id, set(path_node_ids))
        path_entities = [entity_map[nid] for nid in path_node_ids if nid in entity_map]

        return (
            path_entities,
            path_relations,
            {
                "status": "found",
                "depth": len(path_relations),
                "traversal_cost": traversal_cost,
                "query_time_ms": elapsed_ms,
            },
        )

    # ------------------------------------------------------------------
    # Bounded BFS subgraph traversal
    # ------------------------------------------------------------------

    async def bounded_bfs(
        self,
        tenant_id: str,
        start_id: uuid.UUID,
        relation_types: list[str] | None = None,
        max_depth: int = 3,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
        directed: bool = False,
    ) -> tuple[list[AgentKGEntity], list[AgentKGRelation], dict[str, Any]]:
        """
        BFS subgraph traversal from start_id up to max_depth hops.

        Returns (entities, relations, meta).  All queries are tenant-scoped.
        """
        started = time.monotonic()
        deadline = started + timeout_ms / 1000.0

        visited: set[uuid.UUID] = {start_id}
        all_relations: list[AgentKGRelation] = []
        frontier: set[uuid.UUID] = {start_id}
        traversal_cost = 0

        for depth in range(max_depth):
            if not frontier:
                break
            if time.monotonic() > deadline:
                break

            relations = await self._fetch_relations_for_nodes(tenant_id, frontier, relation_types, directed=directed)
            traversal_cost += len(relations)

            next_frontier: set[uuid.UUID] = set()
            for rel in relations:
                if rel not in all_relations:
                    all_relations.append(rel)
                neighbour = rel.target_entity_id if directed or rel.source_entity_id in frontier else rel.source_entity_id
                if neighbour not in visited:
                    visited.add(neighbour)
                    next_frontier.add(neighbour)
                    if len(visited) >= max_nodes:
                        break
            frontier = next_frontier

        elapsed_ms = (time.monotonic() - started) * 1000
        entity_map = await self._fetch_entities_by_ids(tenant_id, visited)
        entities = list(entity_map.values())

        return (
            entities,
            all_relations,
            {
                "status": "found" if entities else "no_path",
                "depth": max_depth,
                "traversal_cost": traversal_cost,
                "query_time_ms": elapsed_ms,
            },
        )

    # ------------------------------------------------------------------
    # Dependency traversal (directed DFS for dependency chains)
    # ------------------------------------------------------------------

    async def dependency_traversal(
        self,
        tenant_id: str,
        start_id: uuid.UUID,
        relation_types: list[str] | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> tuple[list[AgentKGEntity], list[AgentKGRelation], dict[str, Any]]:
        """
        Directed traversal following outgoing edges (dependency direction).
        Uses bounded BFS with directed=True.
        """
        return await self.bounded_bfs(
            tenant_id=tenant_id,
            start_id=start_id,
            relation_types=relation_types,
            max_depth=max_depth,
            max_nodes=max_nodes,
            timeout_ms=timeout_ms,
            directed=True,
        )

    # ------------------------------------------------------------------
    # Query / observability
    # ------------------------------------------------------------------

    async def record_query(self, tenant_id: str, query: str, execution_time_ms: float) -> AgentKGQueryEvent:
        event = AgentKGQueryEvent(tenant_id=tenant_id, query=query, execution_time_ms=execution_time_ms)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    # ------------------------------------------------------------------
    # Provider capabilities
    # ------------------------------------------------------------------

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": "internal_sql",
            "pathfinding": True,
            "algorithms": ["bfs_shortest_path", "bounded_bfs", "dependency_traversal"],
            "relation_filter": True,
            "max_depth": True,
            "max_nodes": True,
            "timeout": True,
            "tenant_isolation": True,
        }
