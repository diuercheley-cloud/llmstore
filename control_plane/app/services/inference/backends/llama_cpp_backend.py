from app.services.inference.backends.base import Capability
from app.services.inference.backends.openai_compatible_backend import OpenAICompatibleBackend


class LlamaCppBackend(OpenAICompatibleBackend):
    """
    Adapter for llama.cpp server, which exposes an OpenAI-compatible API
    when running with `llama-server` or `llama-cli`.
    """

    def supports_capability(self, capability: Capability) -> bool:
        supported = {
            Capability.TEXT,
            Capability.CHAT,
            Capability.STREAMING,
            Capability.EMBEDDINGS,
        }
        return capability in supported
