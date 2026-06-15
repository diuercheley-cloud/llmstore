import logging
from typing import Any

from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.schemas import ProviderCapabilities

logger = logging.getLogger(__name__)


class LocalProvider(ProviderAdapter):
    def __init__(self):
        super().__init__(
            provider_id="local",
            provider_type=ProviderType.LOCAL,
            enabled=True,
            configured=True,
        )

    async def health_check(self) -> dict[str, Any]:
        return {"provider_id": "local", "healthy": True, "latency_ms": 0, "error": None}

    async def list_models(self) -> list[str]:
        return ["mock-model", "local-model"]

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": "local-chat-mock",
            "object": "chat.completion",
            "model": payload.get("model", "local-model"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Local mock response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": "local-resp-mock",
            "object": "response",
            "model": payload.get("model", "local-model"),
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Local mock response"}],
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        }

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "object": "list",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.0] * 4}],
            "model": payload.get("model", "text-embedding-3-small"),
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=True,
            responses=True,
            embeddings=True,
            tools=False,
            vision=False,
            json_mode=True,
            max_context_tokens=8192,
            pricing_configured=False,
        )
