import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.provider_settings import is_real_api_key_configured
from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.schemas import ProviderCapabilities

logger = logging.getLogger(__name__)


class GeminiProvider(ProviderAdapter):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._base_url = settings.gemini_base_url or "https://generativelanguage.googleapis.com/v1beta"
        self._timeout = settings.provider_timeout_seconds
        configured = is_real_api_key_configured(self._api_key)
        enabled = (
            settings.cloud_providers_enabled
            and settings.gemini_provider_enabled
            and settings.real_provider_validation_enabled
        )
        super().__init__(
            provider_id="gemini",
            provider_type=ProviderType.GEMINI,
            enabled=enabled,
            configured=configured,
        )

    async def _client(self) -> httpx.AsyncClient:
        headers = {"Content-Type": "application/json"}
        return httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, headers=headers)

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {"provider_id": "gemini", "healthy": None, "latency_ms": 0, "error": "disabled"}
        if not self.configured:
            return {"provider_id": "gemini", "healthy": None, "latency_ms": 0, "error": "not configured"}
        try:
            async with await self._client() as client:
                resp = await client.get(f"/models?key={self._api_key}")
                return {"provider_id": "gemini", "healthy": resp.is_success, "latency_ms": 0, "error": None}
        except Exception as e:
            return {"provider_id": "gemini", "healthy": False, "latency_ms": 0, "error": str(e)}

    async def list_models(self) -> list[str]:
        if not self.enabled or not self.configured:
            return []
        try:
            async with await self._client() as client:
                resp = await client.get(f"/models?key={self._api_key}")
                if resp.is_success:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        except Exception:
            logger.warning("gemini list_models failed")
        return []

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("model", "gemini-2.0-flash")
        messages = payload.get("messages", [])

        contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                gemini_role = "model" if role in ("assistant", "model") else "user"
                contents.append({"role": gemini_role, "parts": [{"text": content}]})

        body: dict[str, Any] = {"contents": contents}
        if system_instruction:
            body["system_instruction"] = system_instruction
        if payload.get("temperature") is not None:
            body["generationConfig"]["temperature"] = payload["temperature"]
        if payload.get("max_tokens") is not None:
            body["generationConfig"]["maxOutputTokens"] = payload["max_tokens"]
        if payload.get("stop"):
            body["generationConfig"]["stopSequences"] = payload["stop"] if isinstance(payload["stop"], list) else [payload["stop"]]

        async with await self._client() as client:
            resp = await client.post(f"/models/{model}:generateContent?key={self._api_key}", json=body)
            resp.raise_for_status()
            raw = resp.json()
            return self._to_openai_format(raw, model)

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.chat_completion(payload)

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = payload.get("model", "text-embedding-004")
        input_text = payload.get("input", payload.get("input_text", ""))
        if isinstance(input_text, list):
            input_text = " ".join(input_text)

        body = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": input_text}]},
        }
        async with await self._client() as client:
            resp = await client.post(f"/models/{model}:embedContent?key={self._api_key}", json=body)
            resp.raise_for_status()
            raw = resp.json()
            return {
                "object": "list",
                "data": [{"object": "embedding", "embedding": raw.get("embedding", {}).get("values", []), "index": 0}],
                "model": model,
            }

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = {
            "gemini-2.0-flash": (0.10, 0.40),
            "gemini-2.0-flash-lite": (0.075, 0.30),
            "gemini-2.5-pro": (1.25, 10.00),
            "gemini-1.5-pro": (1.25, 5.00),
            "gemini-1.5-flash": (0.075, 0.30),
        }
        key = model.rsplit("/", 1)[-1] if "/" in model else model
        rate = pricing.get(key, pricing.get(model, (0.50, 1.50)))
        return (prompt_tokens * rate[0] + completion_tokens * rate[1]) / 1_000_000

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=True,
            responses=True,
            embeddings=True,
            tools=True,
            vision=True,
            json_mode=True,
            max_context_tokens=1_048_576,
            pricing_configured=True,
        )

    @staticmethod
    def _to_openai_format(gemini_response: dict, model: str) -> dict:
        candidates = gemini_response.get("candidates", [])
        if not candidates:
            return {"choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}]}

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        finish_reason = candidate.get("finishReason", "stop")
        reason_map = {
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter",
            "RECITATION": "content_filter",
            "OTHER": "stop",
        }

        return {
            "id": gemini_response.get("id", ""),
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": reason_map.get(finish_reason, "stop"),
            }],
            "model": model,
            "usage": {
                "prompt_tokens": gemini_response.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": gemini_response.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                "total_tokens": gemini_response.get("usageMetadata", {}).get("totalTokenCount", 0),
            },
        }
