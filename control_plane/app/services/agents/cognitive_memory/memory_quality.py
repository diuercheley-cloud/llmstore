# Owner: agent-platform
from typing import Any


class MemoryQualityService:
    def explain(self, memory) -> dict[str, Any]:
        provenance = getattr(memory, "provenance", {}) or {}
        reliability = 1.0 if provenance else 0.5
        return {
            "confidence": reliability,
            "freshness": "fresh" if getattr(memory, "last_accessed_at", None) else "stale",
            "source_reliability": reliability,
            "poisoning_risk": "low" if provenance else "medium",
        }
