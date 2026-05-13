import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.schemas import ProviderCapabilities

logger = logging.getLogger(__name__)


class OpenAIProvider(ProviderAdapter):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url or "https://api.openai.com/v1"
        self._timeout = settings.provider_timeout_seconds
        self._max_retries = settings.provider_max_retries
        configured = bool(self._api_key)
        super().__init__(
            provider_id="openai",
            provider_type=ProviderType.OPENAI,
            enabled=settings.cloud_providers_enabled,
            configured=configured,
        )

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
        )

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {"provider_id": "openai", "healthy": None, "latency_ms": 0, "error": "disabled"}
        if not self.configured:
            return {"provider_id": "openai", "healthy": None, "latency_ms": 0, "error": "not configured"}
        try:
            async with await self._client() as client:
                resp = await client.get("/models")
                return {"provider_id": "openai", "healthy": resp.is_success, "latency_ms": 0, "error": None}
        except Exception as e:
            return {"provider_id": "openai", "healthy": False, "latency_ms": 0, "error": str(e)}

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
            logger.warning("openai list_models failed")
        return []

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self._client() as client:
            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self._client() as client:
            resp = await client.post("/responses", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self._client() as client:
            resp = await client.post("/embeddings", json=payload)
            resp.raise_for_status()
            return resp.json()

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = {
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4-turbo": (10.00, 30.00),
            "gpt-3.5-turbo": (0.50, 1.50),
            "text-embedding-3-small": (0.02, 0.02),
            "text-embedding-3-large": (0.13, 0.13),
        }
        key = model
        if key not in pricing:
            for pattern, (p, c) in pricing.items():
                if pattern in model:
                    key = pattern
                    break
            else:
                return 0.0
        prompt_price, completion_price = pricing[key]
        return (prompt_tokens / 1_000_000 * prompt_price) + (completion_tokens / 1_000_000 * completion_price)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=True,
            responses=True,
            embeddings=True,
            tools=True,
            vision=True,
            json_mode=True,
            max_context_tokens=128000,
            pricing_configured=True,
        )
