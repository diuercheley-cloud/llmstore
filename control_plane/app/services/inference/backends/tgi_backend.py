from typing import Any, Dict, List

from app.services.inference.backends.base import Capability
from app.services.inference.backends.openai_compatible_backend import OpenAICompatibleBackend


class TGIBackend(OpenAICompatibleBackend):
    def supports_capability(self, capability: Capability) -> bool:
        # TGI specific capabilities
        supported = {
            Capability.TEXT,
            Capability.CHAT,
            Capability.STREAMING,
            Capability.BATCHING
        }
        return capability in supported

    async def health(self) -> bool:
        # TGI health endpoint
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
