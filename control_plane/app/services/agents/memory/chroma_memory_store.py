import logging
import uuid
from typing import Any, Dict, List

from .vector_store import VectorStore

logger = logging.getLogger(__name__)

class ChromaMemoryStore(VectorStore):
    """
    ChromaDB implementation for semantic memory.
    """
    def __init__(self, client=None):
        self.client = client
        self._collection = None

    def _get_collection(self, tenant_id: str):
        # In a real setup, we would use tenant-specific collections or metadata filtering
        if self.client is None:
            try:
                import chromadb
                self.client = chromadb.Client() # ephemeral for example
            except ImportError:
                raise RuntimeError("chromadb package not installed")
        
        return self.client.get_or_create_collection(name=f"agent_memory_{tenant_id}")

    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        collection = self._get_collection(tenant_id)
        
        # Merge agent_id into metadata for filtering
        full_metadata = metadata.copy()
        full_metadata["agent_id"] = str(agent_id)
        
        collection.upsert(
            ids=[str(memory_id)],
            embeddings=[embedding],
            metadatas=[full_metadata]
        )
        logger.debug(f"Chroma store: added item {memory_id} for tenant {tenant_id}")

    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(tenant_id)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"agent_id": str(agent_id)}
        )
        
        scored_items = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                # Chroma returns distances, we convert to score (1 - distance for cosine)
                # assuming cosine distance is used.
                distance = results["distances"][0][i]
                score = 1.0 - distance 
                
                if score >= score_threshold:
                    scored_items.append({
                        "memory_id": uuid.UUID(results["ids"][0][i]),
                        "score": score,
                        "metadata": results["metadatas"][0][i],
                        "provider": "chroma"
                    })
        
        return scored_items

    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        collection = self._get_collection(tenant_id)
        collection.delete(ids=[str(memory_id)])
