from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any


class Capability(str, Enum):
    TEXT = "text"
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    VISION = "vision"
    AUDIO = "audio"
    TOOL_CALLING = "tool_calling"
    STREAMING = "streaming"
    BATCHING = "batching"


class InferenceBackendBase(ABC):
    @abstractmethod
    async def health(self) -> bool:
        """Check if the backend is healthy."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List models available on this backend."""
        pass

    @abstractmethod
    async def infer_chat(
        self, model: str, messages: list[dict[str, Any]], stream: bool = False, **kwargs
    ) -> Any | AsyncIterator[Any]:
        """Perform chat inference."""
        pass

    @abstractmethod
    async def infer_completion(
        self, model: str, prompt: str, stream: bool = False, **kwargs
    ) -> Any | AsyncIterator[Any]:
        """Perform completion inference."""
        pass

    @abstractmethod
    async def infer_embeddings(
        self, model: str, input: str | list[str], **kwargs
    ) -> list[list[float]]:
        """Perform embeddings inference."""
        pass

    @abstractmethod
    def supports_capability(self, capability: Capability) -> bool:
        """Check if the backend supports a specific capability."""
        pass
