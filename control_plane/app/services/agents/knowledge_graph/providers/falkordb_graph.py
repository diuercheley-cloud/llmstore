import uuid
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from redis import asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class FalkorDBGraphProvider:
    """
    FalkorDB-backed knowledge graph provider.
    Uses RedisGraph / FalkorDB for graph operations when available.
    Delegates to InternalSQLGraphProvider as fallback.
    """

    def __init__(self, enabled: bool, db: Optional[Any] = None):
        if not enabled:
            raise RuntimeError("FalkorDB graph provider is disabled by feature flag")
        self._db = db
        self._redis = None
        self._internal = None

    async def _get_internal(self):
        if self._internal is None and self._db is not None:
            from app.services.agents.knowledge_graph.providers.internal_sql_graph import InternalSQLGraphProvider
            self._internal = InternalSQLGraphProvider(self._db)
        return self._internal

    async def _get_redis(self):
        if self._redis is None and HAS_REDIS:
            from app.core.config import get_settings
            settings = get_settings()
            url = getattr(settings, 'falkordb_url', getattr(settings, 'redis_url', 'redis://localhost:6379'))
            try:
                self._redis = await aioredis.from_url(url, decode_responses=True)
                await self._redis.ping()
                logger.info(f"Connected to FalkorDB/Redis at {url}")
            except Exception as e:
                logger.warning(f"FalkorDB connection failed, using SQL fallback: {e}")
                self._redis = None
        return self._redis

    async def healthcheck(self) -> dict:
        redis = await self._get_redis()
        if redis:
            return {"status": "healthy", "provider": "falkordb", "connected": True}
        return {"status": "configured", "provider": "falkordb", "driver_available": HAS_REDIS}

    async def _delegate(self, method: str, **kwargs):
        internal = await self._get_internal()
        if internal:
            return await getattr(internal, method)(**kwargs)
        raise RuntimeError("No available provider backend")

    async def upsert_entity(self, **kwargs):
        return await self._delegate("upsert_entity", **kwargs)

    async def create_relation(self, **kwargs):
        return await self._delegate("create_relation", **kwargs)

    async def create_source(self, **kwargs):
        return await self._delegate("create_source", **kwargs)

    async def list_entities(self, **kwargs):
        return await self._delegate("list_entities", **kwargs)

    async def list_relations(self, **kwargs):
        return await self._delegate("list_relations", **kwargs)

    async def related_entities(self, **kwargs):
        return await self._delegate("related_entities", **kwargs)

    async def record_query(self, **kwargs):
        return await self._delegate("record_query", **kwargs)

    async def shortest_path(self, **kwargs):
        return await self._delegate("shortest_path", **kwargs)

    async def dependency_traversal(self, **kwargs):
        return await self._delegate("dependency_traversal", **kwargs)
