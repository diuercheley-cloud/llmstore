import logging
import uuid
from typing import Any

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class MockMemoryStore(VectorStore):
    """
    In-memory mock vector store for development and fallback.
    """

    def __init__(self):
        self._store: dict[str, list[dict[str, Any]]] = {}

    def clear(self):
        self._store = {}

    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        if tenant_id not in self._store:
            self._store[tenant_id] = []

        # Remove if exists
        self._store[tenant_id] = [
            item for item in self._store[tenant_id] if item["memory_id"] != memory_id
        ]

        self._store[tenant_id].append(
            {
                "memory_id": memory_id,
                "agent_id": agent_id,
                "embedding": embedding,
                "metadata": metadata,
            }
        )
        logger.info(
            f"Mock store INDEX: added item {memory_id} for tenant {tenant_id}, agent {agent_id}. Store size for tenant: {len(self._store[tenant_id])}"
        )

    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        logger.info(
            f"Mock store SEARCH: tenant {tenant_id}, agent {agent_id}. Tenants in store: {list(self._store.keys())}"
        )
        if tenant_id not in self._store:
            return []

        import math

        scored_items = []
        for item in self._store[tenant_id]:
            if str(item["agent_id"]) != str(agent_id):
                continue

            emb = item["embedding"]
            # Proper cosine similarity
            dot = sum(x * y for x, y in zip(query_embedding, emb))
            norm_q = math.sqrt(sum(x * x for x in query_embedding))
            norm_e = math.sqrt(sum(x * x for x in emb))

            score = dot / (norm_q * norm_e) if norm_q > 0 and norm_e > 0 else 0.0

            logger.info(
                f"Mock store EVAL: memory_id={item['memory_id']} score={score} threshold={score_threshold}"
            )

            if score >= score_threshold:
                scored_items.append(
                    {
                        "memory_id": item["memory_id"],
                        "score": score,
                        "metadata": item["metadata"],
                        "provider": "mock",
                    }
                )

        scored_items.sort(key=lambda x: x["score"], reverse=True)
        return scored_items[:top_k]

    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        if tenant_id in self._store:
            self._store[tenant_id] = [
                item for item in self._store[tenant_id] if item["memory_id"] != memory_id
            ]
