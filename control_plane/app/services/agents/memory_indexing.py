"""
Owner: agent-platform
Status: beta
"""
import uuid
import json
import math
import hashlib
import logging
from typing import List, Optional, Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentMemoryIndex, AgentMemorySearchEvent, AgentMemoryItem
from app.core.config import get_settings
from app.services.vectorstores.vectorstore_factory import VectorStoreFactory

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_mock_embedding(text: str, dimensions: int = 384) -> List[float]:
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    embedding = []
    current_hash = hash_bytes
    while len(embedding) < dimensions:
        for i in range(0, len(current_hash), 4):
            if len(embedding) >= dimensions:
                break
            val = int.from_bytes(current_hash[i:i+4], "big")
            float_val = (val / 0xFFFFFFFF)  # [0, 1] range
            embedding.append(round(float(float_val), 6))
        if len(embedding) < dimensions:
            current_hash = hashlib.sha256(current_hash).digest()
    return embedding


class MemoryIndexingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._embedding_service = None

    async def _get_embedding_service(self):
        if self._embedding_service is not None:
            return self._embedding_service
        provider = self.settings.agent_memory_embeddings_provider
        if provider == "local":
            try:
                from app.services.embeddings import get_embedding_service
                self._embedding_service = get_embedding_service()
                return self._embedding_service
            except Exception:
                logger.warning("Local embedding service unavailable, falling back to mock")
        self._embedding_service = None
        return None

    async def _compute_embedding(self, text: str) -> List[float]:
        svc = await self._get_embedding_service()
        if svc:
            try:
                return await svc.embed_text(text)
            except Exception as e:
                logger.warning(f"Embedding service failed, falling back to mock: {e}")
        return get_mock_embedding(text)

    async def index_item(self, tenant_id: str, agent_id: uuid.UUID, item: AgentMemoryItem):
        content = item.raw_content or ""
        embedding = await self._compute_embedding(content)
        
        # Store in Vector DB
        store = VectorStoreFactory.get_instance(session=self.db)
        await store.upsert(
            collection_name="agent_memory",
            id=str(item.id),
            vector=embedding,
            metadata={
                "tenant_id": tenant_id,
                "agent_id": str(agent_id),
                "content": content
            }
        )

        # Update status in local DB
        stmt = select(AgentMemoryIndex).where(AgentMemoryIndex.memory_item_id == item.id)
        res = await self.db.execute(stmt)
        index = res.scalar_one_or_none()

        if not index:
            index = AgentMemoryIndex(
                tenant_id=tenant_id,
                agent_id=agent_id,
                memory_item_id=item.id,
                vector_id=f"vec_{item.id}",
            )
            self.db.add(index)
        
        index.index_status = "completed"
        index.embedding = json.dumps(embedding)
        await self.db.flush()

    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query: str,
        limit: int = 10,
        semantic: bool = False,
    ) -> List[AgentMemoryItem]:
        query_hash = hashlib.sha256(query.encode()).hexdigest()

        if semantic:
            items = await self._semantic_search(tenant_id, agent_id, query, limit)
        else:
            items = await self._like_search(tenant_id, agent_id, query, limit)

        event = AgentMemorySearchEvent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            query_hash=query_hash,
            result_count=len(items),
        )
        self.db.add(event)
        await self.db.commit()
        return items

    async def _like_search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query: str,
        limit: int = 10,
    ) -> List[AgentMemoryItem]:
        stmt = (
            select(AgentMemoryItem)
            .where(
                AgentMemoryItem.tenant_id == tenant_id,
                AgentMemoryItem.agent_id == agent_id,
                AgentMemoryItem.raw_content.ilike(f"%{query}%"),
            )
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def _semantic_search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query: str,
        limit: int = 10,
    ) -> List[AgentMemoryItem]:
        query_emb = await self._compute_embedding(query)

        store = VectorStoreFactory.get_instance(session=self.db)
        hits = await store.search(
            collection_name="agent_memory",
            vector=query_emb,
            limit=limit,
            filters={"tenant_id": tenant_id, "agent_id": str(agent_id)}
        )

        item_ids = []
        for hit in hits:
            try:
                item_ids.append(uuid.UUID(hit["id"]))
            except (ValueError, KeyError, TypeError):
                continue
        
        if not item_ids:
            return []

        stmt = select(AgentMemoryItem).where(AgentMemoryItem.id.in_(item_ids))
        res = await self.db.execute(stmt)
        items_map = {it.id: it for it in res.scalars().all()}

        # Return in the order of hits (similarity score order)
        return [items_map[id] for id in item_ids if id in items_map]
