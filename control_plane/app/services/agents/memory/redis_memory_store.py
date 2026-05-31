import uuid
import json
import math
import logging
from typing import List, Dict, Any, Optional

from redis.asyncio import Redis

from .vector_store import VectorStore

logger = logging.getLogger(__name__)

KEY_PREFIX = "agent:memory:vector"


class RedisMemoryStore(VectorStore):
    """
    Redis-based vector store for agent memory embeddings.
    Uses Redis hashes for item storage and client-side cosine similarity.
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        self._redis = redis_client

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            from app.db.session import redis_client as _rc
            self._redis = _rc
        return self._redis

    def _tenant_key(self, tenant_id: str) -> str:
        return f"{KEY_PREFIX}:{tenant_id}"

    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        r = await self._get_redis()
        key = self._tenant_key(tenant_id)
        item = {
            "agent_id": str(agent_id),
            "memory_id": str(memory_id),
            "embedding": json.dumps(embedding),
            "metadata": json.dumps(metadata),
        }
        await r.hset(key, str(memory_id), json.dumps(item))
        logger.info(
            f"Redis store INDEX: added item {memory_id} for tenant {tenant_id}, agent {agent_id}"
        )

    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        r = await self._get_redis()
        key = self._tenant_key(tenant_id)
        raw_items = await r.hgetall(key)
        if not raw_items:
            return []

        scored = []
        for memory_id_str, item_json in raw_items.items():
            item = json.loads(item_json)
            if item["agent_id"] != str(agent_id):
                continue
            emb = json.loads(item["embedding"])
            dot = sum(x * y for x, y in zip(query_embedding, emb))
            norm_q = math.sqrt(sum(x * x for x in query_embedding))
            norm_e = math.sqrt(sum(x * x for x in emb))
            score = dot / (norm_q * norm_e) if norm_q > 0 and norm_e > 0 else 0.0
            if score >= score_threshold:
                scored.append({
                    "memory_id": uuid.UUID(memory_id_str),
                    "score": score,
                    "metadata": json.loads(item.get("metadata", "{}")),
                    "provider": "redis",
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        r = await self._get_redis()
        key = self._tenant_key(tenant_id)
        await r.hdel(key, str(memory_id))
        logger.info(f"Redis store DELETE: removed item {memory_id} for tenant {tenant_id}")
