from datetime import datetime
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


class GraphQueryRequest(BaseModel):
    tenant_id: str
    query_type: str = "entity_search"
    text: str | None = None
    entity_name: str | None = None
    entity_id: str | None = None
    target_entity_id: str | None = None
    relation_type: str | None = None
    limit: int = 10


class GraphQueryResult(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    context_block: str = ""
    provenance: list[dict[str, Any]] = Field(default_factory=list)
