import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.schemas import ProviderCapabilities

logger = logging.getLogger(__name__)


class AnthropicProvider(ProviderAdapter):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.anthropic_api_key
        self._base_url = settings.anthropic_base_url or "https://api.anthropic.com/v1"
        self._timeout = settings.provider_timeout_seconds
        configured = bool(self._api_key)
        super().__init__(
            provider_id="anthropic",
            provider_type=ProviderType.ANTHROPIC,
            enabled=settings.cloud_providers_enabled,
            configured=configured,
        )

    async def _client(self) -> httpx.AsyncClient:
        headers = {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"} if self._api_key else {}
        return httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, headers=headers)

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {"provider_id": "anthropic", "healthy": None, "latency_ms": 0, "error": "disabled"}
        if not self.configured:
            return {"provider_id": "anthropic", "healthy": None, "latency_ms": 0, "error": "not configured"}
        try:
            async with await self._client() as client:
                resp = await client.get("/models")
                return {"provider_id": "anthropic", "healthy": resp.is_success, "latency_ms": 0, "error": None}
        except Exception as e:
            return {"provider_id": "anthropic", "healthy": False, "latency_ms": 0, "error": str(e)}

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
            logger.warning("anthropic list_models failed")
        return []

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        system = payload.pop("system", None)
        body: dict[str, Any] = {
            "model": payload.get("model"),
            "max_tokens": payload.get("max_tokens", 1024),
            "messages": payload.get("messages", []),
        }
        if system:
            body["system"] = system
        if payload.get("stream"):
            body["stream"] = True
        async with await self._client() as client:
            resp = await client.post("/messages", json=body)
            resp.raise_for_status()
            raw = resp.json()
            return self._to_openai_format(raw, payload.get("model", ""))

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.chat_completion(payload)

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Anthropic does not support embeddings via Messages API")

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = {
            "claude-3-opus": (15.00, 75.00),
            "claude-3-sonnet": (3.00, 15.00),
            "claude-3-haiku": (0.25, 1.25),
            "claude-3-5-sonnet": (3.00, 15.00),
            "claude-3-5-haiku": (0.80, 4.00),
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
            responses=False,
            embeddings=False,
            tools=True,
            vision=True,
            json_mode=True,
            max_context_tokens=200000,
            pricing_configured=True,
        )

    def _to_openai_format(self, raw: dict[str, Any], model: str) -> dict[str, Any]:
        content = ""
        if raw.get("content"):
            for block in raw["content"]:
                if block.get("type") == "text":
                    content = block.get("text", "")
                    break
        return {
            "id": raw.get("id", "anthropic-chat"),
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": raw.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": raw.get("usage", {}).get("output_tokens", 0),
                "total_tokens": raw.get("usage", {}).get("input_tokens", 0) + raw.get("usage", {}).get("output_tokens", 0),
            },
        }
