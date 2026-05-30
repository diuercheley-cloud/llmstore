import abc
import uuid
from typing import List, Dict, Any, Optional

class VectorStore(abc.ABC):
    @abc.abstractmethod
    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        pass

    @abc.abstractmethod
    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        pass
