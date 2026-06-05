import httpx
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
