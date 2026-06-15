# Owner: agent-platform
"""
Hybrid retrieval: vector similarity search + graph traversal.

Design
------
1. A vector search produces an initial candidate set (or falls back to
   entity-name matching when pgvector is not enabled).
2. From each candidate, a bounded BFS explores the local graph neighbourhood.
3. A combined score is computed:
      combined = vector_score * VECTOR_WEIGHT + graph_proximity * GRAPH_WEIGHT
4. Results are deduplicated, ranked by combined score, and returned with full
   provenance (source_id, provider, scores).

Feature flags consulted:
  AGENT_KG_ADJACENCY_CACHE_ENABLED  - caches neighbourhood lookups
  AGENT_KG_PGVECTOR_ENABLED         - real vector search vs ILIKE fallback
  AGENT_KG_PGROUTING_ENABLED        - shortest-path within graph traversal
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.services.agents.knowledge_graph.graph_cache import adjacency_cache
from app.services.agents.knowledge_graph.graph_models import (
    Entity,
    GraphQueryResult,
    Relation,
)
from app.services.agents.knowledge_graph.graph_query_optimizer import (
    OptimizedQueryRequest,
    query_optimizer,
)
from app.services.agents.knowledge_graph.providers.internal_sql_graph import (
    InternalSQLGraphProvider,
)
from sqlalchemy.ext.asyncio import AsyncSession

VECTOR_WEIGHT = 0.6
GRAPH_WEIGHT = 0.4


@dataclass
class HybridCandidate:
    entity: Entity
    vector_score: float = 0.0
    graph_proximity: float = 0.0

    @property
    def combined_score(self) -> float:
        return self.vector_score * VECTOR_WEIGHT + self.graph_proximity * GRAPH_WEIGHT

    def provenance_entry(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity.id,
            "source_id": self.entity.source_id,
            "provenance": self.entity.provenance,
            "vector_score": round(self.vector_score, 4),
            "graph_proximity": round(self.graph_proximity, 4),
            "combined_score": round(self.combined_score, 4),
            "retrieval_method": "hybrid",
        }


@dataclass
class HybridQueryRequest:
    tenant_id: str
    text: str
    query_embedding: Sequence[float] | None = None
    limit: int = 10
    max_depth: int = 2
    max_fan_out: int = 30
    timeout_seconds: float = 8.0
    relation_type: str | None = None


@dataclass
class HybridQueryResult:
    candidates: list[HybridCandidate] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    context_block: str = ""
    provenance: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    explain_plan: dict[str, Any] | None = None

    def to_graph_result(self) -> GraphQueryResult:
        return GraphQueryResult(
            entities=[c.entity for c in self.candidates],
            relations=self.relations,
            context_block=self.context_block,
            provenance=self.provenance,
        )


class VectorGraphHybrid:
    """
    Orchestrates vector search + graph traversal for production GraphRAG.

    Falls back gracefully when pgvector is disabled (uses SQL ILIKE) so
    existing deployments are unaffected until they opt in.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._provider = InternalSQLGraphProvider(db)

    def _get_postgres_provider(self):
        """Lazy import to avoid hard dependency when flag is off."""
        if not self.settings.agent_kg_postgres_graph_enabled:
            return None
        try:
            from app.services.agents.knowledge_graph.providers.postgres_graph import (
                PostgresGraphProvider,
            )

            return PostgresGraphProvider(self.db)
        except Exception:
            return None

    async def _vector_candidates(
        self,
        req: HybridQueryRequest,
    ) -> list[HybridCandidate]:
        """
        Returns candidate entities with a normalised vector_score in [0, 1].
        Uses pgvector when available; falls back to SQL ILIKE with a
        constant score of 0.5.
        """
        pg = self._get_postgres_provider()

        if pg and req.query_embedding:
            entities = await pg.vector_search(
                req.tenant_id,
                req.query_embedding,
                top_k=req.limit * 2,
            )
            # Assign descending score based on rank position
            total = max(len(entities), 1)
            return [
                HybridCandidate(entity=e, vector_score=1.0 - (i / total))
                for i, e in enumerate(entities)
            ]

        # Fallback: text match with constant score
        entities = await self._provider.list_entities(req.tenant_id, entity_name=req.text)
        return [
            HybridCandidate(entity=_orm_to_entity(e), vector_score=0.5)
            for e in entities[: req.limit * 2]
        ]

    async def _expand_graph(
        self,
        req: HybridQueryRequest,
        seed_entities: list[Entity],
    ) -> tuple[dict[str, HybridCandidate], list[Relation]]:
        """
        BFS from each seed entity up to max_depth hops.
        Returns a dict of entity_id → HybridCandidate and all relations seen.
        """
        settings = get_settings()
        cache_enabled = settings.agent_kg_adjacency_cache_enabled

        candidates: dict[str, HybridCandidate] = {}
        all_relations: list[Relation] = []
        visited: set[str] = set()

        queue: list[tuple[Entity, int]] = [(e, 0) for e in seed_entities]

        while queue:
            current_entity, depth = queue.pop(0)
            eid = current_entity.id
            if eid in visited:
                continue
            visited.add(eid)

            # Graph proximity score decreases with depth
            proximity = max(0.0, 1.0 - (depth / max(req.max_depth, 1)))
            if eid not in candidates:
                candidates[eid] = HybridCandidate(
                    entity=current_entity,
                    graph_proximity=proximity,
                )
            else:
                candidates[eid].graph_proximity = max(candidates[eid].graph_proximity, proximity)

            if depth >= req.max_depth:
                continue

            # Try cache first
            cached = adjacency_cache.get(req.tenant_id, eid)
            if cached is not None:
                neighbour_entities, neighbour_relations = cached
            else:
                import uuid as _uuid

                try:
                    eid_uuid = _uuid.UUID(eid)
                except ValueError:
                    continue
                pg = self._get_postgres_provider()
                if pg:
                    neighbour_entities_orm, neighbour_relations_orm = await pg.related_entities(
                        req.tenant_id, eid_uuid, max_fan_out=req.max_fan_out
                    )
                else:
                    (
                        neighbour_entities_orm,
                        neighbour_relations_orm,
                    ) = await self._provider.related_entities(req.tenant_id, eid_uuid)
                neighbour_entities = [_orm_to_entity(e) for e in neighbour_entities_orm]
                neighbour_relations = [_orm_to_relation(r) for r in neighbour_relations_orm]

                # Apply fan-out limit
                neighbour_relations = query_optimizer.apply_fan_out_limit(
                    neighbour_relations, req.max_fan_out
                )

                adjacency_cache.set(req.tenant_id, eid, (neighbour_entities, neighbour_relations))

            for rel in neighbour_relations:
                if rel not in all_relations:
                    all_relations.append(rel)

            for ne in neighbour_entities:
                if ne.id not in visited:
                    queue.append((ne, depth + 1))

        return candidates, all_relations

    async def query(self, req: HybridQueryRequest) -> HybridQueryResult:
        """
        Full hybrid retrieval pipeline with timeout protection.
        """
        opt_req = OptimizedQueryRequest(
            tenant_id=req.tenant_id,
            query_type="hybrid",
            text=req.text,
            limit=req.limit,
            max_depth=req.max_depth,
            max_fan_out=req.max_fan_out,
            timeout_seconds=req.timeout_seconds,
        )
        query_optimizer.validate(opt_req)
        plan = query_optimizer.build_plan(opt_req)

        t0 = time.monotonic()

        async def _inner():
            # 1. Vector phase
            vector_candidates = await self._vector_candidates(req)

            # 2. Graph expansion phase
            seed_entities = [c.entity for c in vector_candidates]
            graph_candidates, relations = await self._expand_graph(req, seed_entities)

            # 3. Merge vector scores into graph candidates
            for vc in vector_candidates:
                eid = vc.entity.id
                if eid in graph_candidates:
                    graph_candidates[eid].vector_score = max(
                        graph_candidates[eid].vector_score, vc.vector_score
                    )
                else:
                    graph_candidates[eid] = vc

            # 4. Rank by combined score, truncate
            ranked = sorted(
                graph_candidates.values(),
                key=lambda c: c.combined_score,
                reverse=True,
            )[: req.limit]

            # 5. Build context block
            entity_lines = "\n".join(
                f"  [{c.entity.type}] {c.entity.name} (score={c.combined_score:.3f})"
                for c in ranked
            )
            provenance = [c.provenance_entry() for c in ranked]
            context_block = (
                f"Hybrid GraphRAG Result for: {req.text!r}\n"
                f"Entities:\n{entity_lines}\n"
                f"Relations found: {len(relations)}\n"
                f"Cache metrics: {adjacency_cache.metrics(req.tenant_id)}\n"
            )

            return ranked, relations, provenance, context_block

        try:
            ranked, relations, provenance, context_block = await query_optimizer.run_with_timeout(
                _inner(), req.timeout_seconds
            )
        except TimeoutError as exc:
            raise TimeoutError(str(exc)) from exc

        latency_ms = (time.monotonic() - t0) * 1000
        return HybridQueryResult(
            candidates=ranked,
            relations=relations,
            context_block=context_block,
            provenance=provenance,
            latency_ms=latency_ms,
            explain_plan=plan.to_dict(),
        )


# ------------------------------------------------------------------
# Helper converters (ORM → Pydantic)
# ------------------------------------------------------------------


def _orm_to_entity(record) -> Entity:
    metadata = getattr(record, "metadata_", None) or {}
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


def _orm_to_relation(record) -> Relation:
    # Use __dict__ to avoid collision with SQLAlchemy's MetaData attribute
    metadata = (
        record.__dict__.get("metadata", {})
        if isinstance(record.__dict__.get("metadata"), dict)
        else {}
    )
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
