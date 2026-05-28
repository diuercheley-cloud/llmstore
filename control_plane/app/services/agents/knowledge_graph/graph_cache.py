# Owner: agent-platform
"""
Adjacency cache for GraphRAG - reduces repeated SQL queries for dense graph traversals.

Feature flag: AGENT_KG_ADJACENCY_CACHE_ENABLED

Design:
- Per-tenant LRU cache keyed by (tenant_id, entity_id)
- TTL-based expiry
- Invalidated on any write to the graph
- Max-size cap per tenant to bound memory usage
- hit/miss counters for observability
"""
from __future__ import annotations

import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


@dataclass
class _TenantCache:
    """LRU store per tenant with TTL and max-size bounds."""
    max_size: int
    ttl_seconds: float
    _store: OrderedDict = field(default_factory=OrderedDict)
    hits: int = 0
    misses: int = 0

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            self.misses += 1
            return None
        # LRU: move to end
        self._store.move_to_end(key)
        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + self.ttl_seconds,
        )
        # Evict LRU if over capacity
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate one key or the entire tenant cache."""
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)

    @property
    def size(self) -> int:
        return len(self._store)

    def metrics(self) -> dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0.0,
            "size": self.size,
        }


class AdjacencyCache:
    """
    Global singleton adjacency cache.

    Each tenant gets its own isolated _TenantCache so cross-tenant cache
    pollution is impossible at the data layer.
    """

    _instance: "AdjacencyCache | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "AdjacencyCache":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tenant_caches: dict[str, _TenantCache] = {}
                cls._instance._global_lock = threading.Lock()
        return cls._instance

    def _get_or_create_tenant_cache(self, tenant_id: str) -> _TenantCache:
        with self._global_lock:
            if tenant_id not in self._tenant_caches:
                settings = get_settings()
                max_size = getattr(settings, "agent_kg_adjacency_cache_max_size", 5000)
                ttl = getattr(settings, "agent_kg_adjacency_cache_ttl_seconds", 300.0)
                self._tenant_caches[tenant_id] = _TenantCache(
                    max_size=max_size,
                    ttl_seconds=ttl,
                )
            return self._tenant_caches[tenant_id]

    def is_enabled(self) -> bool:
        return get_settings().agent_kg_adjacency_cache_enabled

    def get(self, tenant_id: str, entity_id: str) -> Any | None:
        if not self.is_enabled():
            return None
        return self._get_or_create_tenant_cache(tenant_id).get(entity_id)

    def set(self, tenant_id: str, entity_id: str, value: Any) -> None:
        if not self.is_enabled():
            return
        self._get_or_create_tenant_cache(tenant_id).set(entity_id, value)

    def invalidate(self, tenant_id: str, entity_id: str | None = None) -> None:
        """Called on any write; entity_id=None flushes the whole tenant."""
        if not self.is_enabled():
            return
        tc = self._tenant_caches.get(tenant_id)
        if tc is not None:
            tc.invalidate(entity_id)

    def metrics(self, tenant_id: str) -> dict:
        tc = self._tenant_caches.get(tenant_id)
        if tc is None:
            return {"hits": 0, "misses": 0, "hit_rate": 0.0, "size": 0}
        return tc.metrics()

    def all_metrics(self) -> dict[str, dict]:
        return {tid: tc.metrics() for tid, tc in self._tenant_caches.items()}


# Module-level singleton
adjacency_cache = AdjacencyCache()
