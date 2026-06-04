import logging
from typing import Any

import httpx
from app.core.config import get_settings
from app.services.providers.base import ProviderAdapter, ProviderType
from app.services.providers.errors import ProviderNotConfiguredError
from app.services.providers.schemas import ProviderCapabilities

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(ProviderAdapter):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.azure_openai_api_key
        self._endpoint = settings.azure_openai_endpoint
        self._api_version = settings.azure_openai_api_version or "2024-10-21"
        self._deployment = settings.azure_openai_deployment
        self._timeout = settings.provider_timeout_seconds
        configured = bool(self._api_key and self._endpoint)
        enabled = (
            settings.cloud_providers_enabled
            and settings.azure_openai_provider_enabled
            and settings.real_provider_validation_enabled
        )
        super().__init__(
            provider_id="azure_openai",
            provider_type=ProviderType.AZURE_OPENAI,
            enabled=enabled,
            configured=configured,
        )

    async def _client(self) -> httpx.AsyncClient:
        headers = {"api-key": self._api_key, "Content-Type": "application/json"}
        return httpx.AsyncClient(base_url=self._endpoint.rstrip("/"), timeout=self._timeout, headers=headers)

    def _url(self, path: str) -> str:
        deployment = self._deployment or "{deployment}"
        return f"/openai/deployments/{deployment}/{path}?api-version={self._api_version}"

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {"provider_id": "azure_openai", "healthy": None, "latency_ms": 0, "error": "disabled"}
        if not self.configured:
            return {"provider_id": "azure_openai", "healthy": None, "latency_ms": 0, "error": "not configured"}
        try:
            async with await self._client() as client:
                resp = await client.get(self._url("models"))
                return {"provider_id": "azure_openai", "healthy": resp.is_success, "latency_ms": 0, "error": None}
        except Exception as e:
            return {"provider_id": "azure_openai", "healthy": False, "latency_ms": 0, "error": str(e)}

    async def list_models(self) -> list[str]:
        if not self.enabled or not self.configured:
            return []
        deployment = self._deployment or "unknown"
        return [deployment]

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise ProviderNotConfiguredError("Azure OpenAI not configured")

        azure_payload = dict(payload)
        if "model" in azure_payload:
            del azure_payload["model"]

        async with await self._client() as client:
            resp = await client.post(
                self._url("chat/completions"),
                json=azure_payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.chat_completion(payload)

    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise ProviderNotConfiguredError("Azure OpenAI not configured")

        azure_payload = dict(payload)
        if "model" in azure_payload:
            del azure_payload["model"]

        async with await self._client() as client:
            resp = await client.post(
                self._url("embeddings"),
                json=azure_payload,
            )
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
            max_context_tokens=128000,
            pricing_configured=False,
        )
