import logging
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.models.agents.agents import AgentMemoryItem
from app.services.agents.memory_indexing import MemoryIndexingService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .chroma_memory_store import ChromaMemoryStore
from .mock_memory_store import MockMemoryStore
from .pgvector_memory_store import PGVectorMemoryStore
from .pinecone_memory_store import PineconeMemoryStore
from .redis_memory_store import RedisMemoryStore
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

_MOCK_STORE = MockMemoryStore()

class SemanticMemoryRetriever:
    def __init__(self, db: AsyncSession, vector_store: Optional[VectorStore] = None):
        self.db = db
        self.settings = get_settings()
        self.indexing = MemoryIndexingService(db)
        self._vector_store: Optional[VectorStore] = vector_store

    def _get_vector_store(self) -> VectorStore:
        if self._vector_store:
            return self._vector_store
        
        provider = self.settings.agent_memory_vector_provider or "mock"
        if provider == "pgvector":
            self._vector_store = PGVectorMemoryStore(self.db)
        elif provider == "chroma":
            self._vector_store = ChromaMemoryStore()
        elif provider == "redis":
            self._vector_store = RedisMemoryStore()
        elif provider == "pinecone":
            from app.core.config import get_settings
            s = get_settings()
            api_key = getattr(s, 'pinecone_api_key', '') or getattr(s, 'agent_pinecone_api_key', '')
            env = getattr(s, 'pinecone_environment', 'us-east-1-aws')
            index_name = getattr(s, 'pinecone_index_name', 'agent-memory')
            self._vector_store = PineconeMemoryStore(api_key=api_key, environment=env, index_name=index_name)
        else:
            self._vector_store = _MOCK_STORE
        
        return self._vector_store

    async def retrieve_semantic(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Performs real vector search with fallback.
        """
        if not self.settings.agent_semantic_memory_enabled:
            logger.debug("Semantic memory retrieval disabled, skipping.")
            return []

        # 1. Compute query embedding
        query_embedding = await self.indexing._compute_embedding(query)
        
        # 2. Vector search
        store = self._get_vector_store()
        logger.info(f"RETRIEVER: Using store {type(store)} for tenant {tenant_id}, agent {agent_id}")
        matches = await store.search(
            tenant_id=tenant_id,
            agent_id=agent_id,
            query_embedding=query_embedding,
            top_k=top_k,
            score_threshold=score_threshold
        )

        if not matches:
            logger.info(f"RETRIEVER: No matches found for tenant {tenant_id}, agent {agent_id}")
            return []

        # 3. Hydrate results from DB
        memory_ids = [m["memory_id"] for m in matches]
        stmt = select(AgentMemoryItem).where(AgentMemoryItem.id.in_(memory_ids))
        res = await self.db.execute(stmt)
        items = {item.id: item for item in res.scalars().all()}

        final_results = []
        for match in matches:
            mid = match["memory_id"]
            if mid in items:
                item = items[mid]
                final_results.append({
                    "memory_id": str(mid),
                    "content": item.raw_content,
                    "summary": item.summary,
                    "score": round(match["score"], 4),
                    "provider": match["provider"],
                    "memory_type": item.memory_type,
                    "metadata": item.provenance or {},
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                })
        
        return final_results

    async def index_memory(self, tenant_id: str, agent_id: uuid.UUID, item: AgentMemoryItem):
        """
        Indexes a single memory item into the vector store.
        """
        embedding = await self.indexing._compute_embedding(item.raw_content or "")
        store = self._get_vector_store()
        await store.add_item(
            tenant_id=tenant_id,
            agent_id=agent_id,
            memory_id=item.id,
            embedding=embedding,
            metadata={"memory_type": item.memory_type}
        )
