from __future__ import annotations

import uuid
from typing import Any

from app.api.deps import get_db_session, require_admin
from app.services.agents.agent_graph.engine import AgentGraphEngine
from app.services.agents.agent_graph.models import (
    AgentGraphSpec,
    AgentNode,
    AgentNodeType,
    GraphEdge,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/agents/graphs",
    tags=["agent-graph"],
    dependencies=[Depends(require_admin)],
)


# ── Request / Response schemas ──────────────────────────────────────


class NodeSchema(BaseModel):
    id: str
    type: AgentNodeType
    agent_id: str | None = None
    name: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    input: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 2
    timeout_seconds: int = 300


class EdgeSchema(BaseModel):
    source: str
    target: str
    condition: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class GraphCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    nodes: list[NodeSchema] = Field(..., min_length=1)
    edges: list[EdgeSchema] = Field(default_factory=list)
    max_concurrency: int = 5
    enable_checkpointing: bool = True


class GraphRunSchema(BaseModel):
    global_input: dict[str, Any] = Field(default_factory=dict)


class GraphRunRequest(BaseModel):
    graph: GraphCreateSchema
    global_input: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    run_id: str
    status: str
    started_at: str = ""
    completed_at: str = ""
    error: str | None = None
    node_results: dict[str, Any] = Field(default_factory=dict)


# ── Engine instance (shared) ────────────────────────────────────────

_engine: AgentGraphEngine | None = None


def get_engine() -> AgentGraphEngine:
    global _engine
    if _engine is None:
        _engine = AgentGraphEngine()
    return _engine


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/run", response_model=GraphResponse)
async def run_graph(
    body: GraphRunRequest,
    db: AsyncSession = Depends(get_db_session),
):
    engine = get_engine()
    spec = _to_graph_spec(body.graph)
    result = await engine.execute(spec, global_input=body.global_input)
    return _to_response(result)


@router.get("/runs", response_model=list[dict[str, Any]])
async def list_graph_runs(db: AsyncSession = Depends(get_db_session)):
    engine = get_engine()
    return engine.list_runs()


@router.get("/runs/{run_id}", response_model=GraphResponse)
async def get_graph_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    engine = get_engine()
    result = engine.get_status(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_response(result)


@router.post("/runs/{run_id}/cancel", response_model=dict[str, Any])
async def cancel_graph_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    engine = get_engine()
    ok = engine.cancel(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Run not found or already completed")
    return {"status": "cancelled", "run_id": run_id}


@router.post("/validate", response_model=dict[str, Any])
async def validate_graph(graph: GraphCreateSchema):
    engine = get_engine()
    spec = _to_graph_spec(graph)
    # Validate: no duplicate IDs
    ids = [n.id for n in spec.nodes]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Duplicate node IDs")
    # Validate: edges reference existing nodes
    node_ids = set(ids)
    for edge in spec.edges:
        if edge.source not in node_ids:
            raise HTTPException(
                status_code=400, detail=f"Edge source '{edge.source}' not found in nodes"
            )
        if edge.target not in node_ids:
            raise HTTPException(
                status_code=400, detail=f"Edge target '{edge.target}' not found in nodes"
            )
    # Validate: no cycles
    if engine._detect_cycle({n.id: n for n in spec.nodes}, _build_adj(spec)):
        raise HTTPException(
            status_code=400, detail="Graph contains a cycle. Remove cycles to proceed."
        )
    # Return topological order
    order = engine.topological_sort(spec)
    return {
        "valid": True,
        "topological_order": order,
        "node_count": len(spec.nodes),
        "edge_count": len(spec.edges),
    }


# ── Helpers ─────────────────────────────────────────────────────────


def _to_graph_spec(schema: GraphCreateSchema) -> AgentGraphSpec:
    return AgentGraphSpec(
        nodes=[
            AgentNode(
                id=n.id,
                type=n.type,
                agent_id=uuid.UUID(n.agent_id) if n.agent_id else None,
                name=n.name,
                config=n.config,
                input=n.input,
                max_retries=n.max_retries,
                timeout_seconds=n.timeout_seconds,
            )
            for n in schema.nodes
        ],
        edges=[
            GraphEdge(source=e.source, target=e.target, condition=e.condition, data=e.data)
            for e in schema.edges
        ],
        name=schema.name,
        description=schema.description,
        max_concurrency=schema.max_concurrency,
        enable_checkpointing=schema.enable_checkpointing,
    )


def _build_adj(spec: AgentGraphSpec) -> dict[str, list[GraphEdge]]:
    adj: dict[str, list[GraphEdge]] = {n.id: [] for n in spec.nodes}
    for edge in spec.edges:
        adj.setdefault(edge.source, []).append(edge)
    return adj


def _to_response(result: Any) -> GraphResponse:
    return GraphResponse(
        run_id=result.run_id,
        status=result.status.value if hasattr(result.status, "value") else str(result.status),
        started_at=result.started_at,
        completed_at=result.completed_at,
        error=result.error,
        node_results={
            nid: {
                "node_id": nr.node_id,
                "status": nr.status.value if hasattr(nr.status, "value") else str(nr.status),
                "output": nr.output,
                "error": nr.error,
                "duration_ms": nr.duration_ms,
                "retry_attempts": nr.retry_attempts,
            }
            for nid, nr in (result.node_results or {}).items()
        },
    )
