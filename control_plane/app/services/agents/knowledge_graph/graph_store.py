# Owner: agent-platform
"""
GraphStore — tenant-isolated Knowledge Graph façade.

Routing rules for query_type == "path":
  - internal_sql / postgres providers: real BFS pathfinding via provider.shortest_path()
  - external providers (neo4j, falkordb) without pathfinding support:
    returns PathStatus.capability_not_supported (never a mock empty list)
  - mock mode (AGENT_KG_MOCK_MODE=true): returns PathStatus.mock with empty
    path and a warning in the reason field — ONLY for test/staging.

An empty path list is ONLY returned when:
  - status == PathStatus.no_path  (genuine dead-end, no route exists)
  - status == PathStatus.timeout  (search aborted due to time budget)
  - status == PathStatus.capability_not_supported (provider does not implement pathfinding)
  - status == PathStatus.mock (mock mode, test only)
"""
from __future__ import annotations

import hashlib
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

from .graph_cache import adjacency_cache
from .graph_models import Entity, GraphQueryRequest, GraphQueryResult, PathResult, PathStatus, Relation
from .graph_policy import graph_policy
from .providers.falkordb_graph import FalkorDBGraphProvider
from .providers.internal_sql_graph import InternalSQLGraphProvider
from .providers.neo4j_graph import Neo4jGraphProvider


class GraphStore:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.provider = self._get_provider()

    def _get_provider(self):
        provider_name = self.settings.agent_kg_provider
        if provider_name == "neo4j":
            return Neo4jGraphProvider(enabled=self.settings.agent_kg_external_provider_enabled, db=self.db)
        if provider_name == "falkordb":
            return FalkorDBGraphProvider(enabled=self.settings.agent_kg_external_provider_enabled, db=self.db)
        if provider_name == "postgres" or self.settings.agent_kg_postgres_graph_enabled:
            try:
                from .providers.postgres_graph import PostgresGraphProvider
                return PostgresGraphProvider(self.db)
            except Exception:
                pass  # fall through to internal_sql
        return InternalSQLGraphProvider(self.db)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def add_entity(self, tenant_id: str, name: str, entity_type: str, source_id: uuid.UUID | None = None) -> Entity:
        graph_policy.require_writes_enabled(self.settings.agent_kg_write_enabled)
        record = await self.provider.upsert_entity(
            tenant_id=tenant_id,
            name=graph_policy.redact_secrets(name),
            entity_type=entity_type,
            source_id=source_id,
            provenance={"provider": self.settings.agent_kg_provider},
        )
        adjacency_cache.invalidate(tenant_id)
        return self._entity_to_model(record)

    async def add_relation(
        self,
        tenant_id: str,
        src_id: str,
        tgt_id: str,
        relation_type: str,
        provenance: str,
        source_id: uuid.UUID | None = None,
    ) -> Relation:
        graph_policy.require_writes_enabled(self.settings.agent_kg_write_enabled)
        record = await self.provider.create_relation(
            tenant_id=tenant_id,
            source_entity_id=uuid.UUID(src_id),
            target_entity_id=uuid.UUID(tgt_id),
            relation_type=relation_type,
            provenance=provenance,
            source_id=source_id,
        )
        adjacency_cache.invalidate(tenant_id, src_id)
        adjacency_cache.invalidate(tenant_id, tgt_id)
        return self._relation_to_model(record)

    async def create_source(self, tenant_id: str, uri: str, raw_text: str) -> uuid.UUID:
        sanitized = graph_policy.redact_secrets(raw_text)
        source = await self.provider.create_source(
            tenant_id=tenant_id,
            uri=uri,
            content_hash=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
        )
        return source.id

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_entities(self, tenant_id: str, entity_name: str | None = None) -> list[Entity]:
        records = await self.provider.list_entities(tenant_id=tenant_id, entity_name=entity_name)
        return [self._entity_to_model(record) for record in records]

    async def get_relations(self, tenant_id: str, entity_id: str | None = None) -> list[Relation]:
        parsed_entity_id = uuid.UUID(entity_id) if entity_id else None
        records = await self.provider.list_relations(tenant_id=tenant_id, entity_id=parsed_entity_id)
        return [self._relation_to_model(record) for record in records]

    # ------------------------------------------------------------------
    # Unified query dispatcher
    # ------------------------------------------------------------------

    async def query(self, request: GraphQueryRequest) -> GraphQueryResult:
        graph_policy.validate_tenant(request.tenant_id)
        started_at = time.time()
        entities: list[Entity] = []
        relations: list[Relation] = []
        path: PathResult | None = None

        if request.query_type == "entity_search":
            entities = await self.get_entities(request.tenant_id, entity_name=request.entity_name or request.text)

        elif request.query_type in {"neighborhood", "owners"} and request.entity_id:
            records, record_relations = await self.provider.related_entities(
                request.tenant_id, uuid.UUID(request.entity_id)
            )
            entities = [self._entity_to_model(r) for r in records]
            relations = [self._relation_to_model(r) for r in record_relations]

        elif request.query_type == "dependencies" and request.entity_id:
            path = await self._run_dependency_traversal(request, started_at)
            entities = path.nodes
            relations = path.edges

        elif request.query_type == "path" and request.entity_id and request.target_entity_id:
            path = await self._run_shortest_path(request, started_at)
            entities = path.nodes
            relations = path.edges

        await self.provider.record_query(
            tenant_id=request.tenant_id,
            query=request.text or request.entity_name or request.query_type,
            execution_time_ms=(time.time() - started_at) * 1000,
        )

        provenance = [
            {"entity_id": e.id, "source_id": e.source_id, "provenance": e.provenance}
            for e in entities
        ]
        return GraphQueryResult(
            entities=entities[: request.limit],
            relations=relations[: request.limit],
            provenance=provenance,
            path=path,
        )

    # ------------------------------------------------------------------
    # Pathfinding dispatch helpers
    # ------------------------------------------------------------------

    async def _run_shortest_path(self, request: GraphQueryRequest, started_at: float) -> PathResult:
        """
        Dispatch shortest-path to provider.  Returns PathResult with full
        provenance, confidence, traversal_cost, and query_time_ms.

        Decision matrix:
          - mock mode → PathStatus.mock (test/staging only)
          - provider without .shortest_path() → PathStatus.capability_not_supported
          - no route in graph → PathStatus.no_path
          - route found → PathStatus.found with populated nodes/edges
        """
        # Mock mode: only allowed when AGENT_KG_MOCK_MODE=true
        if self.settings.agent_kg_mock_mode:
            return PathResult(
                status=PathStatus.mock,
                nodes=[],
                edges=[],
                reason="AGENT_KG_MOCK_MODE=true — real pathfinding disabled for this environment",
                query_time_ms=(time.time() - started_at) * 1000,
            )

        # Check provider capability
        if not hasattr(self.provider, "shortest_path"):
            return PathResult(
                status=PathStatus.capability_not_supported,
                nodes=[],
                edges=[],
                reason=f"Provider '{type(self.provider).__name__}' does not implement shortest_path",
                query_time_ms=(time.time() - started_at) * 1000,
            )

        src_uuid = uuid.UUID(request.entity_id)  # type: ignore[arg-type]
        tgt_uuid = uuid.UUID(request.target_entity_id)  # type: ignore[arg-type]
        relation_types = [request.relation_type] if request.relation_type else None

        path_entities, path_relations, meta = await self.provider.shortest_path(
            tenant_id=request.tenant_id,
            source_id=src_uuid,
            target_id=tgt_uuid,
            relation_types=relation_types,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            timeout_ms=request.timeout_ms,
        )

        status = PathStatus(meta.get("status", "no_path"))
        nodes = [self._entity_to_model(e) for e in path_entities]
        edges = [self._relation_to_model(r) for r in path_relations]
        relation_types_found = list({e.type for e in edges})
        provenance = [
            {"entity_id": n.id, "source_id": n.source_id, "provenance": n.provenance}
            for n in nodes
        ]
        confidence = min((e.confidence for e in edges), default=1.0)
        reason = "" if status == PathStatus.found else f"status={status.value}"

        return PathResult(
            status=status,
            nodes=nodes,
            edges=edges,
            relation_types=relation_types_found,
            provenance=provenance,
            confidence=confidence,
            traversal_cost=meta.get("traversal_cost", 0),
            query_time_ms=meta.get("query_time_ms", (time.time() - started_at) * 1000),
            depth=meta.get("depth", 0),
            reason=reason,
        )

    async def _run_dependency_traversal(self, request: GraphQueryRequest, started_at: float) -> PathResult:
        """Directed dependency traversal via provider.dependency_traversal()."""
        if self.settings.agent_kg_mock_mode:
            return PathResult(
                status=PathStatus.mock,
                nodes=[],
                edges=[],
                reason="AGENT_KG_MOCK_MODE=true",
                query_time_ms=(time.time() - started_at) * 1000,
            )

        if not hasattr(self.provider, "dependency_traversal"):
            return PathResult(
                status=PathStatus.capability_not_supported,
                nodes=[],
                edges=[],
                reason=f"Provider '{type(self.provider).__name__}' does not implement dependency_traversal",
                query_time_ms=(time.time() - started_at) * 1000,
            )

        relation_types = [request.relation_type] if request.relation_type else None
        dep_entities, dep_relations, meta = await self.provider.dependency_traversal(
            tenant_id=request.tenant_id,
            start_id=uuid.UUID(request.entity_id),  # type: ignore[arg-type]
            relation_types=relation_types,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            timeout_ms=request.timeout_ms,
        )

        status = PathStatus(meta.get("status", "no_path"))
        nodes = [self._entity_to_model(e) for e in dep_entities]
        edges = [self._relation_to_model(r) for r in dep_relations]
        relation_types_found = list({e.type for e in edges})
        provenance = [
            {"entity_id": n.id, "source_id": n.source_id, "provenance": n.provenance}
            for n in nodes
        ]

        return PathResult(
            status=status,
            nodes=nodes,
            edges=edges,
            relation_types=relation_types_found,
            provenance=provenance,
            confidence=min((e.confidence for e in edges), default=1.0),
            traversal_cost=meta.get("traversal_cost", 0),
            query_time_ms=meta.get("query_time_ms", (time.time() - started_at) * 1000),
            depth=meta.get("depth", 0),
        )

    # ------------------------------------------------------------------
    # Model converters
    # ------------------------------------------------------------------

    def _entity_to_model(self, record) -> Entity:
        metadata = record.metadata_ or {}
        return Entity(
            id=str(record.id),
            tenant_id=record.tenant_id,
            source_id=metadata.get("source_id"),
            name=record.name,
            type=record.type,
            provenance=metadata.get("provenance", {}),
            confidence=metadata.get("confidence", 1.0),
            freshness=metadata.get("freshness"),
            created_at=record.created_at,
            updated_at=record.updated_at,
            metadata=metadata,
        )

    def _relation_to_model(self, record) -> Relation:
        # AgentKGRelation has no mapped `metadata` column.  The provider stores
        # transient metadata in record.__dict__["metadata"] (not persisted to DB).
        # BFS-fetched relations (loaded fresh from DB) will not have this key.
        # We must NOT use getattr() because SQLAlchemy Base exposes a class-level
        # `metadata` attribute (a MetaData object) that getattr() would return
        # when the per-instance key is absent.
        raw = record.__dict__.get("metadata")
        metadata: dict = raw if isinstance(raw, dict) else {}
        return Relation(
            id=str(record.id),
            tenant_id=record.tenant_id,
            source_id=metadata.get("source_id"),
            source_entity_id=str(record.source_entity_id),
            target_entity_id=str(record.target_entity_id),
            type=record.relation_type,
            provenance=record.source_provenance,
            confidence=metadata.get("confidence", 1.0),
            freshness=metadata.get("freshness"),
            created_at=record.created_at,
            updated_at=getattr(record, "updated_at", None),
            metadata=metadata,
        )
