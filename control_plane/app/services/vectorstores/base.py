import abc
from typing import Any


class VectorStoreBase(abc.ABC):
    """
    Common interface for all vector database providers.
    """

    @abc.abstractmethod
    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> None:
        """
        Insert or update a vector in the store.
        """
        pass

    @abc.abstractmethod
    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors.
        """
        pass

    @abc.abstractmethod
    async def delete(
        self,
        collection_name: str,
        ids: list[str],
        namespace: str | None = None,
    ) -> None:
        """
        Delete vectors by ID.
        """
        pass

    @abc.abstractmethod
    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Create a new collection.
        """
        pass

    @abc.abstractmethod
    async def collection_delete(
        self,
        collection_name: str,
    ) -> None:
        """
        Delete a collection.
        """
        pass

    @abc.abstractmethod
    async def healthcheck(self) -> dict[str, Any]:
        """
        Check the health of the vector store.
        """
        pass
