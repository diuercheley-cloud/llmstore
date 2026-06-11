from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InferenceCapability(str, Enum):
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    BATCHING = "batching"


@dataclass(slots=True)
class BackendCapabilities:
    streaming: bool = False
    embeddings: bool = False
    tool_calling: bool = False
    vision: bool = False
    batching: bool = False
    notes: list[str] = field(default_factory=list)

    def supports(self, capability: InferenceCapability) -> bool:
        return bool(getattr(self, capability.value, False))

    def model_dump(self) -> dict[str, Any]:
        return {
            "streaming": self.streaming,
            "embeddings": self.embeddings,
            "tool_calling": self.tool_calling,
            "vision": self.vision,
            "batching": self.batching,
            "notes": list(self.notes),
        }


class InferenceBackend:
    def capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    async def health(self) -> dict[str, Any]:
        raise NotImplementedError

    async def list_models(self) -> list[str]:
        raise NotImplementedError

    async def benchmark(self) -> dict[str, Any]:
        raise NotImplementedError
