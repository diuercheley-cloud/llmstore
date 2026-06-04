# Owner: agent-platform
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_ENTITY_TYPES = [
    "person",
    "organization",
    "project",
    "system",
    "contract",
    "document",
    "process",
    "asset",
    "risk",
    "ticket",
    "repository",
    "agent",
    "tool",
]
DEFAULT_RELATION_TYPES = [
    "owns",
    "depends_on",
    "manages",
    "references",
    "blocks",
    "implements",
    "violates",
    "approves",
    "uses",
    "belongs_to",
    "related_to",
]


class Entity(BaseModel):
    id: str
    tenant_id: str
    source_id: str | None = None
    name: str
    type: str
    provenance: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    freshness: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Relation(BaseModel):
    id: str
    tenant_id: str
    source_id: str | None = None
    source_entity_id: str
    target_entity_id: str
    type: str
    provenance: str
    confidence: float = 1.0
    freshness: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PathStatus(str, Enum):
    """Outcome of a pathfinding operation."""

    found = "found"
    no_path = "no_path"
    timeout = "timeout"
    capability_not_supported = "capability_not_supported"
    mock = "mock"


class PathResult(BaseModel):
    """
    Result of a graph pathfinding / traversal query.

    Every successful traversal includes:
    - nodes: entities visited along the path
    - edges: relations traversed
    - relation_types: set of distinct relation types encountered
    - provenance: per-node source / document references
    - confidence: minimum confidence across all traversed edges
    - traversal_cost: number of edges relaxed during search
    - query_time_ms: wall-clock time of the pathfinding call

    When status != PathStatus.found the path will be empty and
    ``reason`` will carry a human-readable explanation.
    """

    status: PathStatus = PathStatus.no_path
    nodes: list[Entity] = Field(default_factory=list)
    edges: list[Relation] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    traversal_cost: int = 0
    query_time_ms: float = 0.0
    depth: int = 0
    reason: str = ""


class GraphQueryRequest(BaseModel):
    tenant_id: str
    query_type: str = "entity_search"
    text: str | None = None
    entity_name: str | None = None
    entity_id: str | None = None
    target_entity_id: str | None = None
    relation_type: str | None = None
    # Pathfinding controls
    max_depth: int = 6
    max_nodes: int = 500
    timeout_ms: int = 5000
    limit: int = 10


class GraphQueryResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    context_block: str = ""
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    # Populated when query_type == "path"
    path: PathResult | None = None
