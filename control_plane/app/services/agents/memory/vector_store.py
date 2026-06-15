import abc
import uuid
from typing import Any


class VectorStore(abc.ABC):
    @abc.abstractmethod
    async def add_item(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        memory_id: uuid.UUID,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        pass

    @abc.abstractmethod
    async def search(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def delete_item(
        self,
        tenant_id: str,
        memory_id: uuid.UUID,
    ) -> None:
        pass
