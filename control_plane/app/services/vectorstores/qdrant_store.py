import logging
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import get_settings

from .base import VectorStoreBase

logger = logging.getLogger(__name__)
settings = get_settings()

class QdrantStore(VectorStoreBase):
    """
    Qdrant implementation of the VectorStore interface using REST API.
    """

    def __init__(self):
        self.url = settings.qdrant_url
        self.api_key = settings.qdrant_api_key
        self.headers = {}
        if self.api_key:
            self.headers["api-key"] = self.api_key

    async def _request(self, method: str, path: str, json_data: Any = None) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, f"{self.url}{path}", json=json_data, headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> None:
        point = {
            "id": id,
            "vector": vector,
            "payload": metadata or {}
        }
        await self._request("PUT", f"/collections/{collection_name}/points", {"points": [point]})

    async def search(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = {
            "vector": vector,
            "limit": limit,
            "with_payload": True
        }
        if filters:
            # Simple Qdrant filter conversion (can be expanded)
            q_filter = {"must": []}
            for k, v in filters.items():
                q_filter["must"].append({"key": k, "match": {"value": v}})
            query["filter"] = q_filter

        res = await self._request("POST", f"/collections/{collection_name}/points/search", query)
        hits = []
        for hit in res.get("result", []):
            hits.append({
                "id": hit["id"],
                "metadata": hit.get("payload", {}),
                "score": hit["score"]
            })
        return hits

    async def delete(
        self,
        collection_name: str,
        ids: List[str],
        namespace: Optional[str] = None,
    ) -> None:
        await self._request("POST", f"/collections/{collection_name}/points/delete", {"points": ids})

    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        body = {
            "vectors": {
                "size": dimension,
                "distance": "Cosine"
            }
        }
        await self._request("PUT", f"/collections/{collection_name}", body)

    async def collection_delete(
        self,
        collection_name: str,
    ) -> None:
        await self._request("DELETE", f"/collections/{collection_name}")

    async def healthcheck(self) -> Dict[str, Any]:
        if not settings.qdrant_enabled:
            return {"status": "disabled", "provider": "qdrant"}
        try:
            res = await self._request("GET", "/health")
            return {
                "status": "healthy" if res.get("title") == "qdrant" else "unhealthy",
                "version": res.get("version"),
                "provider": "qdrant"
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "provider": "qdrant"}
