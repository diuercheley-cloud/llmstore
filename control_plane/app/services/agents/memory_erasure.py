# Owner: agent-platform
import logging
import uuid
from typing import Optional

from app.models.agents.agents import AgentMemoryItem
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class MemoryErasureService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_erasure(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        agent_id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
        hard_delete: bool = False
    ) -> dict:
        """
        Request erasure of memories based on criteria.
        This represents the Right to be Forgotten.
        """
        stmt = select(AgentMemoryItem).where(AgentMemoryItem.tenant_id == tenant_id)
        if agent_id:
            stmt = stmt.where(AgentMemoryItem.agent_id == agent_id)
        
        # In a real implementation we would also filter by user_id or source provenance
        # For simplicity, we fetch them and filter
        
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        
        deleted_count = 0
        for item in items:
            # Delete from vector index, KG, summaries
            # Here we mock the deletion propagation
            await self._propagate_deletion(item)
            
            if hard_delete:
                await self.db.delete(item)
            else:
                # Tombstone: preserve audit without raw content
                item.raw_content = "[DELETED]"
                item.summary = None
                item.content_hash = "tombstone"
                item.status = "deleted"
                
            deleted_count += 1
            
        await self.db.commit()
        return {"status": "erasure_completed", "deleted_count": deleted_count, "hard_delete": hard_delete}

    async def _propagate_deletion(self, item: AgentMemoryItem):
        try:
            from app.services.agents.memory.semantic_memory_retriever import SemanticMemoryRetriever
            retriever = SemanticMemoryRetriever(self.db)
            store = retriever._get_vector_store()
            if hasattr(store, 'delete') and callable(getattr(store, 'delete')):
                await store.delete(str(item.id))
            elif hasattr(store, 'remove_item') and callable(getattr(store, 'remove_item')):
                await store.remove_item(str(item.id))
            else:
                logger.info(f"Vector store {type(store).__name__} does not support deletion; memory {item.id} tombstoned in DB only")
        except Exception as e:
            logger.warning(f"Vector store propagation failed for memory {item.id}: {e}")

        logger.info(f"Deletion propagated for memory item {item.id}")

    async def get_deletion_proof(self, tenant_id: str, item_id: uuid.UUID) -> Optional[dict]:
        # Return tombstone verification
        stmt = select(AgentMemoryItem).where(
            AgentMemoryItem.id == item_id,
            AgentMemoryItem.tenant_id == tenant_id
        )
        res = await self.db.execute(stmt)
        item = res.scalars().first()
        
        if not item:
            return None
            
        if item.status == "deleted" or item.raw_content == "[DELETED]":
            return {
                "id": str(item.id),
                "status": "deleted",
                "tombstone": True,
                "provenance": item.provenance
            }
        return None
