import httpx
from fastapi import HTTPException
from app.core.config import get_settings
from app.services.inference.backends.base import Capability
from app.services.inference.backends.openai_compatible_backend import OpenAICompatibleBackend


class VLLMBackend(OpenAICompatibleBackend):
    def supports_capability(self, capability: Capability) -> bool:
        supported = {
            Capability.TEXT,
            Capability.CHAT,
            Capability.STREAMING,
            Capability.TOOL_CALLING,
            Capability.BATCHING,
        }
        return capability in supported

    async def health(self) -> bool:
        try:
            response = await self.client.get("/health")
            if response.status_code == 200:
                return True
        except Exception:
            pass

        return await super().health()


class VllmBackendService:
    """Utility service for vLLM health checks and model listing."""

    def __init__(self):
        self.settings = get_settings()

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.vllm_base_url,
            timeout=httpx.Timeout(self.settings.data_plane_timeout_seconds),
        )

    def _resolve_model(self, model: str | None) -> str:
        if not model or model == "default":
            return self.settings.vllm_default_model
        return model

    async def chat_completions(self, payload: dict, stream: bool = False) -> dict:
        request_payload = dict(payload)
        request_payload["model"] = self._resolve_model(request_payload.get("model"))

        try:
            async with self._get_client() as client:
                response = await client.post("/v1/chat/completions", json=request_payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail=f"vLLM request timed out: {exc}") from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"vLLM request failed: {exc}") from exc
