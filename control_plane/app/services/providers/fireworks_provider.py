import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.provider_settings import is_real_api_key_configured
from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.schemas import ProviderCapabilities

logger = logging.getLogger(__name__)


class FireworksProvider(ProviderAdapter):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.fireworks_api_key
        self._base_url = "https://api.fireworks.ai/inference/v1"
        self._timeout = settings.provider_timeout_seconds
        configured = is_real_api_key_configured(self._api_key)
        enabled = settings.cloud_providers_enabled and settings.fireworks_provider_enabled
        super().__init__(
            provider_id="fireworks",
            provider_type=ProviderType.FIREWORKS,
            enabled=enabled,
            configured=configured,
        )

    async def _client(self) -> httpx.AsyncClient:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        return httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, headers=headers)

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {"provider_id": "fireworks", "healthy": None, "latency_ms": 0, "error": "disabled"}
        if not self.configured:
            return {"provider_id": "fireworks", "healthy": None, "latency_ms": 0, "error": "not configured"}
        try:
            async with await self._client() as client:
                resp = await client.get("/models")
                return {"provider_id": "fireworks", "healthy": resp.is_success, "latency_ms": 0, "error": None}
        except Exception as e:
            return {"provider_id": "fireworks", "healthy": False, "latency_ms": 0, "error": str(e)}

    async def list_models(self) -> list[str]:
        if not self.enabled or not self.configured:
            return []
        try:
            async with await self._client() as client:
                resp = await client.get("/models")
                if resp.is_success:
                    data = resp.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            logger.warning("fireworks list_models failed")
        return []

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self._client() as client:
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self._client() as client:
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self._client() as client:
            resp = await client.post("/embeddings", json=payload)
            resp.raise_for_status()
            return resp.json()

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=True,
            responses=True,
            embeddings=True,
            tools=True,
            vision=True,
            json_mode=True,
            max_context_tokens=131072,
            pricing_configured=False,
        )
