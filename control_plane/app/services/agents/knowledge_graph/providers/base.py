# Owner: agent-platform
from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

from app.models.agent_knowledge_graph import AgentKGEntity, AgentKGExtractionRun, AgentKGRelation, AgentKGSource, AgentKGQueryEvent

@runtime_checkable
class GraphProvider(Protocol):
    """
    Standard interface for all Knowledge Graph providers.
    
    All implementations (Postgres, Neo4j, FalkorDB, InternalSQL) must
    adhere to this contract to ensure GraphStore can dispatch queries
    without provider-specific branching.
    """

    async def create_source(self, tenant_id: str, uri: str, content_hash: str | None = None) -> AgentKGSource: ...

    async def create_extraction_run(self, tenant_id: str, document_id: str | None = None) -> AgentKGExtractionRun: ...

    async def upsert_entity(
        self,
        tenant_id: str,
        name: str,
        entity_type: str,
        source_id: uuid.UUID | None = None,
        provenance: dict[str, Any] | None = None,
        confidence: float = 1.0,
        freshness: str = "fresh",
    ) -> AgentKGEntity: ...

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
    ) -> AgentKGRelation: ...

    async def list_entities(self, tenant_id: str, entity_name: str | None = None) -> list[AgentKGEntity]: ...

    async def list_relations(self, tenant_id: str, entity_id: uuid.UUID | None = None) -> list[AgentKGRelation]: ...

    async def related_entities(self, tenant_id: str, entity_id: uuid.UUID) -> tuple[list[AgentKGEntity], list[AgentKGRelation]]: ...

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
        Find the shortest path between two entities.
        
        Returns:
            (path_entities, path_relations, metadata)
            metadata must contain 'status' (found, no_path, timeout, etc.)
        """
        ...

    async def dependency_traversal(
        self,
        tenant_id: str,
        start_id: uuid.UUID,
        relation_types: list[str] | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ) -> tuple[list[AgentKGEntity], list[AgentKGRelation], dict[str, Any]]: ...

    async def record_query(self, tenant_id: str, query: str, execution_time_ms: float) -> AgentKGQueryEvent: ...

    def capabilities(self) -> dict[str, Any]: ...
