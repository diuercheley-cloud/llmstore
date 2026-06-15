import logging
from typing import Any

import httpx
from app.core.config import get_settings

from .base import VectorStoreBase

logger = logging.getLogger(__name__)
settings = get_settings()


class MilvusStore(VectorStoreBase):
    """
    Milvus implementation of the VectorStore interface using REST API v2.
    """

    def __init__(self):
        self.url = settings.milvus_url
        self.token = settings.milvus_token
        self.headers = {"Content-Type": "application/json"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def _request(self, method: str, path: str, json_data: Any = None) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, f"{self.url}/v2/vectordb{path}", json=json_data, headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> None:
        data = {
            "collectionName": collection_name,
            "data": [{"id": id, "vector": vector, **(metadata or {})}],
        }
        await self._request("POST", "/entities/upsert", data)

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        query = {
            "collectionName": collection_name,
            "vector": vector,
            "limit": limit,
            "outputFields": ["*"],
        }
        if filters:
            # Simple Milvus filter (Boolean expression)
            filter_parts = []
            for k, v in filters.items():
                if isinstance(v, str):
                    filter_parts.append(f'{k} == "{v}"')
                else:
                    filter_parts.append(f"{k} == {v}")
            query["filter"] = " and ".join(filter_parts)

        res = await self._request("POST", "/entities/search", query)
        hits = []
        for hit in res.get("data", []):
            hits.append({"id": hit.get("id"), "metadata": hit, "score": hit.get("distance", 0.0)})
        return hits

    async def delete(
        self,
        collection_name: str,
        ids: list[str],
        namespace: str | None = None,
    ) -> None:
        filter_str = f"id in {ids}"
        await self._request(
            "POST", "/entities/delete", {"collectionName": collection_name, "filter": filter_str}
        )

    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Simplified Milvus collection creation
        body = {"collectionName": collection_name, "dimension": dimension}
        await self._request("POST", "/collections/create", body)

    async def collection_delete(
        self,
        collection_name: str,
    ) -> None:
        await self._request("POST", "/collections/drop", {"collectionName": collection_name})

    async def healthcheck(self) -> dict[str, Any]:
        if not settings.milvus_enabled:
            return {"status": "disabled", "provider": "milvus"}
        try:
            # Milvus doesn't have a simple /health in REST v2, so we list collections
            await self._request("POST", "/collections/list", {})
            return {"status": "healthy", "provider": "milvus"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "provider": "milvus"}
