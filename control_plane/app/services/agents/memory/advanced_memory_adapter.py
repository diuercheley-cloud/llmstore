import uuid
from typing import Any, Dict, List, Optional

from app.services.agents.memory.advanced_memory_service import AdvancedMemoryService
from app.models.advanced_memory import MemoryScope, MemoryEventType
from sqlalchemy.ext.asyncio import AsyncSession


class AdvancedMemoryAdapter:
    """
    Adapter to allow the existing AgentMemoryService to use the AdvancedMemoryService
    when the feature flag is enabled.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.advanced_service = AdvancedMemoryService(db)

    async def write_memory(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_type: str,
        content: str,
        importance: float = 1.0,
        **kwargs
    ):
        # Map string memory_type to MemoryScope
        scope_map = {
            "short_term": MemoryScope.SHORT_TERM,
            "long_term": MemoryScope.EPISODIC,
            "episodic": MemoryScope.EPISODIC,
            "semantic": MemoryScope.SEMANTIC,
            "relational": MemoryScope.RELATIONAL,
            "vector": MemoryScope.VECTOR,
            "graph": MemoryScope.GRAPH,
            "workflow": MemoryScope.WORKFLOW_STATE
        }
        scope = scope_map.get(memory_type, MemoryScope.EPISODIC)
        
        await self.advanced_service.append_event(
            tenant_id=tenant_id,
            agent_id=agent_id,
            scope=scope,
            event_type=MemoryEventType.CREATED,
            payload={"content": content, **kwargs},
            importance_score=importance
        )
