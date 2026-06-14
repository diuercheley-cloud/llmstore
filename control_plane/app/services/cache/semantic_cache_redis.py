from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.metrics import record_semantic_cache_result
from app.services.embeddings import get_embedding_service
from redis.asyncio import Redis

logger = logging.getLogger(__name__)
settings = get_settings()

class SemanticCacheRedis:
    def __init__(self, redis: Redis):
        self.redis = redis
        self._embedding_service = None

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def _get_key_prefix(self, tenant_id: str, client_id: str, model: str) -> str:
        # Namespace por tenant/client_id e model
        return f"semcache:{tenant_id}:{client_id}:{model}"

    def _generate_id(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    async def get(
        self, 
        tenant_id: str, 
        client_id: str, 
        model: str, 
        prompt: str
    ) -> Optional[Dict[str, Any]]:
        if not settings.semantic_cache_enabled:
            return None

        start_time = time.perf_counter()
        prefix = self._get_key_prefix(tenant_id, client_id, model)
        entries_key = f"{prefix}:entries"
        
        try:
            # 1. Get embedding for the prompt
            query_vector = await self.embedding_service.embed_text(prompt)
            
            # 2. Fetch all entries for this model/client
            # Note: For large scale, use Redis Vector Similarity Search (RediSearch)
            # Fetching all entries and computing similarity in-memory for now
            # as it matches the pattern of existing intelligent_cache.py
            all_entries = await self.redis.hgetall(entries_key)
            if not all_entries:
                self._record_miss(model, tenant_id, client_id, start_time)
                return None

            best_score = -1.0
            best_payload = None
            best_entry_id = None
            embedding_model = self.embedding_service.model_name

            for entry_id, entry_json in all_entries.items():
                try:
                    entry = json.loads(entry_json)
                    
                    # Invalidation by model version
                    if entry.get("emb_model") != embedding_model:
                        continue

                    stored_vector = entry.get("vec")
                    if not stored_vector or len(stored_vector) != len(query_vector):
                        continue

                    score = self._cosine_similarity(query_vector, stored_vector)
                    if score > best_score:
                        best_score = score
                        best_payload = entry.get("resp")
                        best_entry_id = entry_id
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue

            if best_payload and best_score >= settings.semantic_cache_threshold:
                # Update last used in ZSET for LRU
                await self.redis.zadd(f"{prefix}:access", {best_entry_id: time.time()})
                self._record_hit(model, tenant_id, client_id, start_time)
                return best_payload

            self._record_miss(model, tenant_id, client_id, start_time)
            return None
        except Exception as e:
            logger.error(f"Semantic cache lookup error: {e}")
            return None

    async def set(
        self, 
        tenant_id: str, 
        client_id: str, 
        model: str, 
        prompt: str, 
        response: Dict[str, Any]
    ) -> None:
        if not settings.semantic_cache_enabled:
            return

        prefix = self._get_key_prefix(tenant_id, client_id, model)
        entries_key = f"{prefix}:entries"
        access_key = f"{prefix}:access"

        try:
            embedding = await self.embedding_service.embed_text(prompt)
            entry_id = self._generate_id(prompt)
            now = time.time()
            
            entry = {
                "p": prompt,
                "resp": response,
                "vec": embedding,
                "emb_model": self.embedding_service.model_name,
                "ts": now,
            }

            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(entries_key, entry_id, json.dumps(entry))
                pipe.zadd(access_key, {entry_id: now})
                # Use semantic_cache_ttl_seconds
                pipe.expire(entries_key, settings.semantic_cache_ttl_seconds)
                pipe.expire(access_key, settings.semantic_cache_ttl_seconds)
                await pipe.execute()

            await self._enforce_limit(prefix)
        except Exception as e:
            logger.error(f"Semantic cache store error: {e}")

    async def _enforce_limit(self, prefix: str) -> None:
        access_key = f"{prefix}:access"
        entries_key = f"{prefix}:entries"

        count = await self.redis.zcard(access_key)
        if count > settings.semantic_cache_max_size:
            to_remove = count - settings.semantic_cache_max_size
            old_entries = await self.redis.zpopmin(access_key, to_remove)
            if old_entries:
                entry_ids = [e[0] for e in old_entries]
                await self.redis.hdel(entries_key, *entry_ids)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _record_hit(self, model, tenant_id, client_id, start_time):
        record_semantic_cache_result(
            hit=True,
            model=model,
            tenant_id=tenant_id,
            client_id=client_id,
            latency_seconds=time.perf_counter() - start_time
        )

    def _record_miss(self, model, tenant_id, client_id, start_time):
        record_semantic_cache_result(
            hit=False,
            model=model,
            tenant_id=tenant_id,
            client_id=client_id,
            latency_seconds=time.perf_counter() - start_time
        )

_semantic_cache = None

def get_semantic_cache(redis: Redis) -> SemanticCacheRedis:
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCacheRedis(redis)
    return _semantic_cache
