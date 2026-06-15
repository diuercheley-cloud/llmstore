# Owner: agent-platform
"""
GraphRAG Query Optimizer - prevents runaway recursive traversals in dense graphs.

Controls:
- max_depth: limits BFS/DFS hop count
- max_fan_out: limits neighbours explored per node
- timeout_seconds: hard wall-clock timeout
- explain_plan: returns a simplified query plan for observability
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings

# Defaults
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_FAN_OUT = 50
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass
class QueryPlan:
    query_type: str
    tenant_id: str
    max_depth: int
    max_fan_out: int
    timeout_seconds: float
    estimated_nodes: int = 0
    steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query_type": self.query_type,
            "tenant_id": self.tenant_id,
            "max_depth": self.max_depth,
            "max_fan_out": self.max_fan_out,
            "timeout_seconds": self.timeout_seconds,
            "estimated_nodes": self.estimated_nodes,
            "steps": self.steps,
            "warnings": self.warnings,
        }


@dataclass
class OptimizedQueryRequest:
    tenant_id: str
    query_type: str
    entity_id: str | None = None
    target_entity_id: str | None = None
    text: str | None = None
    entity_name: str | None = None
    relation_type: str | None = None
    limit: int = 10
    max_depth: int = DEFAULT_MAX_DEPTH
    max_fan_out: int = DEFAULT_MAX_FAN_OUT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    explain: bool = False


class GraphQueryOptimizer:
    """
    Wraps graph queries with depth/fan-out limiting and timeout enforcement.
    Provides an explain() method that returns a simplified query plan without
    executing the actual traversal.
    """

    def __init__(self):
        settings = get_settings()
        self._default_max_depth: int = getattr(
            settings, "agent_kg_query_max_depth", DEFAULT_MAX_DEPTH
        )
        self._default_max_fan_out: int = getattr(
            settings, "agent_kg_query_max_fan_out", DEFAULT_MAX_FAN_OUT
        )
        self._default_timeout: float = getattr(
            settings, "agent_kg_query_timeout_seconds", DEFAULT_TIMEOUT_SECONDS
        )

    def build_plan(self, req: OptimizedQueryRequest) -> QueryPlan:
        """Generate a simplified explain plan without executing the query."""
        plan = QueryPlan(
            query_type=req.query_type,
            tenant_id=req.tenant_id,
            max_depth=req.max_depth,
            max_fan_out=req.max_fan_out,
            timeout_seconds=req.timeout_seconds,
        )

        if req.query_type == "entity_search":
            plan.steps = [
                f"SeqScan agent_kg_entities WHERE tenant_id=? AND name ILIKE '%{req.text or req.entity_name}%'",
                f"Limit {req.limit}",
            ]
            plan.estimated_nodes = req.limit

        elif req.query_type in {"neighborhood", "dependencies", "owners"}:
            plan.steps = [
                "IndexScan agent_kg_relations ON (tenant_id, source_entity_id) WHERE entity_id=?",
                f"BFS traversal depth_limit={req.max_depth} fan_out_limit={req.max_fan_out}",
                "Fetch entities for visited IDs",
                f"Limit {req.limit}",
            ]
            # Compute raw upper-bound BEFORE capping to detect large traversals
            raw_estimated = req.max_fan_out**req.max_depth
            if raw_estimated > 10_000:
                plan.warnings.append(
                    f"Estimated {raw_estimated:,} nodes - consider reducing max_depth or max_fan_out"
                )
            plan.estimated_nodes = min(raw_estimated, req.limit * 10)

        elif req.query_type == "path":
            plan.steps = [
                "BFS shortest path from entity_id to target_entity_id",
                f"depth_limit={req.max_depth}",
                f"fan_out_limit={req.max_fan_out}",
            ]
            plan.estimated_nodes = req.max_depth * req.max_fan_out

        elif req.query_type == "hybrid":
            plan.steps = [
                "VectorSearch pgvector/cosine top-k candidates",
                f"Graph traversal from vector matches depth={req.max_depth}",
                "Score combination (vector_score * 0.6 + graph_proximity_score * 0.4)",
                "Deduplicate by entity_id",
                f"Limit {req.limit}",
            ]
            plan.estimated_nodes = req.limit * 5

        return plan

    def validate(self, req: OptimizedQueryRequest) -> None:
        """Raise if limits are exceeded or request is invalid."""
        max_depth_cap = getattr(get_settings(), "agent_kg_query_max_depth_hard_cap", 10)
        max_fan_out_cap = getattr(get_settings(), "agent_kg_query_max_fan_out_hard_cap", 200)

        if req.max_depth > max_depth_cap:
            raise ValueError(f"max_depth={req.max_depth} exceeds hard cap of {max_depth_cap}")
        if req.max_fan_out > max_fan_out_cap:
            raise ValueError(f"max_fan_out={req.max_fan_out} exceeds hard cap of {max_fan_out_cap}")
        if req.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    async def run_with_timeout(
        self,
        coro,
        timeout_seconds: float,
    ) -> Any:
        """Execute a coroutine with a hard timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except TimeoutError:
            raise TimeoutError(f"Graph query exceeded timeout of {timeout_seconds:.1f}s")

    def apply_fan_out_limit(
        self,
        neighbours: list[Any],
        max_fan_out: int,
    ) -> list[Any]:
        """Truncate a neighbour list to max_fan_out, preserving order."""
        if len(neighbours) > max_fan_out:
            return neighbours[:max_fan_out]
        return neighbours


# Module-level singleton
query_optimizer = GraphQueryOptimizer()
