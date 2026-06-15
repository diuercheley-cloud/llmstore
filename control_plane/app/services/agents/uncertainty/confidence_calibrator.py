# Owner: agent-platform
from typing import Any


class ConfidenceCalibrator:
    def calculate(self, metrics: dict[str, Any]) -> float:
        """
        Calculates a calibrated confidence score between 0.0 and 1.0.
        Formula (Heuristic):
          base = (evidence_score * 0.4) + (source_coverage * 0.2) + (tool_result_consistency * 0.4)
          penalty = (contradiction_score * 0.5) + (memory_conflict_score * 0.3)
        """
        evidence = metrics.get("evidence_score", 0.5)
        coverage = metrics.get("source_coverage", 0.5)
        consistency = metrics.get("tool_result_consistency", 1.0)

        contradiction = metrics.get("contradiction_score", 0.0)
        conflict = metrics.get("memory_conflict_score", 0.0)

        base_score = (evidence * 0.4) + (coverage * 0.2) + (consistency * 0.4)
        penalty = (contradiction * 0.5) + (conflict * 0.3)

        score = max(0.0, min(1.0, base_score - penalty))
        return round(score, 3)
