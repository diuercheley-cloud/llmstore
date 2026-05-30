import abc
from typing import List, Dict, Any, Optional

class VectorStoreBase(abc.ABC):
    """
    Common interface for all vector database providers.
    """

    @abc.abstractmethod
    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """
        Insert or update a vector in the store.
        """
        pass

    @abc.abstractmethod
    async def search(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        """
        pass

    @abc.abstractmethod
    async def delete(
        self,
        collection_name: str,
        ids: List[str],
        namespace: Optional[str] = None,
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
        metadata: Optional[Dict[str, Any]] = None,
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
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check the health of the vector store.
        """
        pass
