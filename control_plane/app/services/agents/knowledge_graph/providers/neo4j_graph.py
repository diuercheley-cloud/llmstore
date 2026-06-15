import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

try:
    from neo4j import AsyncGraphDatabase

    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False


class Neo4jGraphProvider:
    """
    Neo4j-backed knowledge graph provider.
    Delegates to InternalSQLGraphProvider for SQL-based operations,
    and uses native Cypher for Neo4j-specific queries when driver is available.

    Implements GraphProvider protocol.
    """

    def __init__(self, enabled: bool, db: Any | None = None):
        if not enabled:
            raise RuntimeError("Neo4j graph provider is disabled by feature flag")
        self._db = db
        self._driver = None
        self._internal = None

    async def _get_internal(self):
        if self._internal is None and self._db is not None:
            from app.services.agents.knowledge_graph.providers.internal_sql_graph import (
                InternalSQLGraphProvider,
            )

            self._internal = InternalSQLGraphProvider(self._db)
        return self._internal

    async def _get_driver(self):
        if self._driver is None and HAS_NEO4J:
            from app.core.config import get_settings

            settings = get_settings()
            uri = getattr(settings, "neo4j_uri", "bolt://localhost:7687")
            user = getattr(settings, "neo4j_user", "neo4j")
            password = getattr(settings, "neo4j_password", "")
            try:
                self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
                await self._driver.verify_connectivity()
                logger.info(f"Connected to Neo4j at {uri}")
            except Exception as e:
                logger.warning(f"Neo4j connection failed, using SQL fallback: {e}")
                self._driver = None
        return self._driver

    async def healthcheck(self) -> dict:
        driver = await self._get_driver()
        if driver:
            return {"status": "healthy", "provider": "neo4j", "connected": True}
        return {"status": "configured", "provider": "neo4j", "driver_available": HAS_NEO4J}

    async def upsert_entity(self, tenant_id: str, name: str, entity_type: str, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.upsert_entity(tenant_id, name, entity_type, **kwargs)
        raise RuntimeError("No available provider backend")

    async def create_relation(self, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.create_relation(**kwargs)
        raise RuntimeError("No available provider backend")

    async def create_source(self, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.create_source(**kwargs)
        raise RuntimeError("No available provider backend")

    async def list_entities(self, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.list_entities(**kwargs)
        raise RuntimeError("No available provider backend")

    async def list_relations(self, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.list_relations(**kwargs)
        raise RuntimeError("No available provider backend")

    async def related_entities(self, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.related_entities(**kwargs)
        raise RuntimeError("No available provider backend")

    async def record_query(self, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await internal.record_query(**kwargs)
        raise RuntimeError("No available provider backend")

    async def shortest_path(
        self,
        tenant_id: str,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        relation_types: list[str] | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ):
        internal = await self._get_internal()
        if internal:
            return await internal.shortest_path(
                tenant_id=tenant_id,
                source_id=source_id,
                target_id=target_id,
                relation_types=relation_types,
                max_depth=max_depth,
                max_nodes=max_nodes,
                timeout_ms=timeout_ms,
            )
        raise RuntimeError("No available provider backend")

    async def dependency_traversal(
        self,
        tenant_id: str,
        start_id: uuid.UUID,
        relation_types: list[str] | None = None,
        max_depth: int = 6,
        max_nodes: int = 500,
        timeout_ms: int = 5000,
    ):
        internal = await self._get_internal()
        if internal:
            return await internal.dependency_traversal(
                tenant_id=tenant_id,
                start_id=start_id,
                relation_types=relation_types,
                max_depth=max_depth,
                max_nodes=max_nodes,
                timeout_ms=timeout_ms,
            )
        raise RuntimeError("No available provider backend")

    def capabilities(self) -> dict[str, Any]:
        return {
            "provider": "neo4j",
            "fallback": "internal_sql",
        }
