# Owner: agent-platform
from typing import Any

from .memory_quality import MemoryQualityService


class MemoryExplainabilityService:
    def __init__(self):
        self.quality = MemoryQualityService()

    def build(self, memory, reason: str) -> dict[str, Any]:
        return {
            "memory_id": str(memory.id),
            "reason": reason,
            "policy": "tenant-scoped retrieval",
            "provenance": memory.provenance,
            "quality": self.quality.explain(memory),
        }
