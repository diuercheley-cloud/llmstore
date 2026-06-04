import logging
import uuid
from typing import Any, Dict, List, Optional

from app.services.agents.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone, ServerlessSpec
    HAS_PINECONE = True
except ImportError:
    HAS_PINECONE = False


class PineconeMemoryStore(VectorStore):
    """
    Pinecone vector store backend for agent memory.
    Uses the official Pinecone Python client.
    Gracefully degrades when Pinecone is unavailable.
    """

    def __init__(self, api_key: Optional[str] = None, environment: Optional[str] = None, index_name: str = "agent-memory"):
        self._api_key = api_key
        self._environment = environment or "us-east-1-aws"
        self._index_name = index_name
        self._index = None
        self._pc = None
        self._dimension = 384

        if HAS_PINECONE and api_key:
            try:
                self._pc = Pinecone(api_key=api_key)
                self._ensure_index()
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}")

    def _ensure_index(self):
        if not self._pc:
            return
        try:
            if self._index_name not in self._pc.list_indexes().names():
                self._pc.create_index(
                    name=self._index_name,
                    dimension=self._dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=self._environment),
                )
            self._index = self._pc.Index(self._index_name)
        except Exception as e:
            logger.warning(f"Pinecone index setup failed: {e}")

    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        if not self._index:
            logger.warning("Pinecone not available, skipping add_item")
            return

        vector_id = f"{tenant_id}:{agent_id}:{memory_id}"
        augmented_metadata = {
            "tenant_id": tenant_id,
            "agent_id": str(agent_id),
            "memory_id": str(memory_id),
            **metadata,
        }
        try:
            self._index.upsert(vectors=[(vector_id, embedding, augmented_metadata)])
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {e}")

    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        if not self._index:
            logger.warning("Pinecone not available, returning empty results")
            return []

        filter_dict = {"tenant_id": tenant_id, "agent_id": str(agent_id)}

        try:
            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True,
            )
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            return []

        matches = []
        for match in results.get("matches", []):
            score = match.get("score", 0.0)
            if score < score_threshold:
                continue
            meta = match.get("metadata", {})
            matches.append({
                "memory_id": meta.get("memory_id", ""),
                "score": score,
                "provider": "pinecone",
                "metadata": meta,
            })

        return matches

    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        if not self._index:
            return

        vector_id_prefix = f"{tenant_id}:"
        try:
            self._index.delete(filter={"tenant_id": tenant_id, "memory_id": str(memory_id)})
        except Exception as e:
            logger.error(f"Pinecone delete failed: {e}")
