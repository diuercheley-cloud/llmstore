import logging
import uuid
from typing import Any, Dict, List

from app.models.agents import AgentMemoryIndex
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .vector_store import VectorStore

logger = logging.getLogger(__name__)

class PGVectorMemoryStore(VectorStore):
    """
    PostgreSQL pgvector implementation for semantic memory.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        # We reuse the AgentMemoryIndex table, assuming it has a 'vector' column for pgvector
        # or we use the 'embedding' Text column if pgvector is not natively mapped in SQLAlchemy yet
        # For this implementation, we assume semantic retrieval via SQL-level distance
        
        # Check if exists
        stmt = select(AgentMemoryIndex).where(
            AgentMemoryIndex.tenant_id == tenant_id,
            AgentMemoryIndex.memory_item_id == memory_id
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()

        import json
        if item:
            item.embedding = json.dumps(embedding)
            item.index_status = "completed"
        else:
            item = AgentMemoryIndex(
                tenant_id=tenant_id,
                agent_id=agent_id,
                memory_item_id=memory_id,
                embedding=json.dumps(embedding),
                index_status="completed"
            )
            self.db.add(item)
        
        await self.db.flush()

    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        # In a real pgvector setup, we would use:
        # SELECT memory_item_id, 1 - (embedding <=> :q) as score ...
        # Since we are using SQLAlchemy and might not have the extension mapped:
        
        import json

        from sqlalchemy import text

        # Fallback to loading all embeddings for this tenant/agent if native vector search is not configured
        # But here we implement the intended SQL logic
        q_json = json.dumps(query_embedding)
        
        sql = text("""
            SELECT memory_item_id, 
                   (1 - (embedding_vector <=> CAST(:q AS vector))) as score
            FROM agent_memory_indexes
            WHERE tenant_id = :t AND agent_id = :a
              AND (1 - (embedding_vector <=> CAST(:q AS vector))) >= :threshold
            ORDER BY score DESC
            LIMIT :k
        """)
        
        try:
            res = await self.db.execute(sql, {"q": q_json, "t": tenant_id, "a": str(agent_id), "threshold": score_threshold, "k": top_k})
            results = []
            for row in res:
                results.append({
                    "memory_id": row[0],
                    "score": float(row[1]),
                    "provider": "pgvector"
                })
            return results
        except Exception as e:
            logger.error(f"pgvector search failed, possibly extension missing: {e}")
            # Real fallback to manual calculation in memory if pgvector fails
            return await self._manual_fallback_search(tenant_id, agent_id, query_embedding, top_k, score_threshold)

    async def _manual_fallback_search(self, tenant_id, agent_id, query_embedding, top_k, score_threshold):
        import json
        import math
        
        stmt = select(AgentMemoryIndex).where(
            AgentMemoryIndex.tenant_id == tenant_id,
            AgentMemoryIndex.agent_id == agent_id,
            AgentMemoryIndex.embedding.isnot(None)
        )
        res = await self.db.execute(stmt)
        items = res.scalars().all()
        
        scored = []
        for it in items:
            emb = json.loads(it.embedding)
            # Cosine similarity
            dot = sum(x * y for x, y in zip(query_embedding, emb))
            norm_q = math.sqrt(sum(x * x for x in query_embedding))
            norm_i = math.sqrt(sum(y * y for y in emb))
            score = dot / (norm_q * norm_i) if norm_q > 0 and norm_i > 0 else 0
            
            if score >= score_threshold:
                scored.append({"memory_id": it.memory_item_id, "score": score, "provider": "pgvector-fallback"})
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        stmt = select(AgentMemoryIndex).where(
            AgentMemoryIndex.tenant_id == tenant_id,
            AgentMemoryIndex.memory_item_id == memory_id
        )
        res = await self.db.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            await self.db.delete(item)
            await self.db.flush()
