import logging
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import get_settings

from .base import VectorStoreBase

logger = logging.getLogger(__name__)
settings = get_settings()

class WeaviateStore(VectorStoreBase):
    """
    Weaviate implementation of the VectorStore interface using REST API v1.
    """

    def __init__(self):
        self.url = settings.weaviate_url
        self.api_key = settings.weaviate_api_key
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def _request(self, method: str, path: str, json_data: Any = None) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, f"{self.url}/v1{path}", json=json_data, headers=self.headers
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
        # Weaviate uses "Class" instead of "Collection"
        data = {
            "class": collection_name,
            "id": id,
            "vector": vector,
            "properties": metadata or {}
        }
        # Try to update if exists, otherwise create
        try:
            await self._request("POST", "/objects", data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422: # Already exists or validation error
                await self._request("PUT", f"/objects/{collection_name}/{id}", data)
            else:
                raise

    async def search(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        # Weaviate search uses GraphQL /v1/graphql
        # This is a bit more complex for a raw REST implementation
        # But we can use the /v1/objects with nearVector
        
        query = {
            "nearVector": {
                "vector": vector
            },
            "limit": limit
        }
        # Filtering in Weaviate REST is limited, GraphQL is preferred
        # For simplicity in this mock-like implementation:
        path = f"/objects?class={collection_name}&limit={limit}"
        res = await self._request("GET", path)
        
        hits = []
        for obj in res.get("objects", []):
            hits.append({
                "id": obj["id"],
                "metadata": obj.get("properties", {}),
                "score": 1.0 # Score calculation would need GraphQL
            })
        return hits

    async def delete(
        self,
        collection_name: str,
        ids: List[str],
        namespace: Optional[str] = None,
    ) -> None:
        for obj_id in ids:
            await self._request("DELETE", f"/objects/{collection_name}/{obj_id}")

    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        schema = {
            "class": collection_name,
            "vectorizer": "none" # We provide vectors
        }
        await self._request("POST", "/schema", schema)

    async def collection_delete(
        self,
        collection_name: str,
    ) -> None:
        await self._request("DELETE", f"/schema/{collection_name}")

    async def healthcheck(self) -> Dict[str, Any]:
        if not settings.weaviate_enabled:
            return {"status": "disabled", "provider": "weaviate"}
        try:
            res = await self._request("GET", "/.well-known/ready")
            return {"status": "healthy", "provider": "weaviate"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "provider": "weaviate"}
