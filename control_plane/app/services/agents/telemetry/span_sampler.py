# Owner: agent-platform
import random

from app.services.agents.telemetry.span_priority import (
    SpanPriority,
    classify_span_priority,
    should_never_drop,
)


class SpanSampler:
    def __init__(self):
        self._sample_rates: dict[SpanPriority, float] = {
            SpanPriority.CRITICAL: 1.0,
            SpanPriority.HIGH: 1.0,
            SpanPriority.NORMAL: 0.5,
            SpanPriority.DEBUG: 0.1,
        }

    def set_sample_rate(self, priority: SpanPriority, rate: float) -> None:
        self._sample_rates[priority] = max(0.0, min(1.0, rate))

    def get_sample_rate(self, priority: SpanPriority) -> float:
        return self._sample_rates.get(priority, 0.5)

    def should_sample(self, span_type: str, priority: SpanPriority | None = None) -> bool:
        if priority is None:
            priority = classify_span_priority(span_type)
        rate = self._sample_rates.get(priority, 0.5)
        if rate >= 1.0:
            return True
        if rate <= 0.0:
            return False
        return random.random() < rate

    def select_spans_to_drop(
        self,
        queue: list[dict],
        target_remove: int,
    ) -> list[int]:
        indices_by_priority: dict[SpanPriority, list[int]] = {p: [] for p in SpanPriority}
        for idx, span in enumerate(queue):
            span_type = span.get("type", "")
            priority = classify_span_priority(span_type)
            if not should_never_drop(priority):
                indices_by_priority[priority].append(idx)

        to_drop: list[int] = []
        for priority in sorted(SpanPriority, reverse=True):
            if len(to_drop) >= target_remove:
                break
            indices = indices_by_priority.get(priority, [])
            if priority == SpanPriority.DEBUG:
                to_drop.extend(indices[: target_remove - len(to_drop)])
            elif priority == SpanPriority.NORMAL:
                sample_count = min(len(indices), target_remove - len(to_drop))
                to_drop.extend(random.sample(indices, sample_count))
            elif priority == SpanPriority.HIGH:
                sample_count = min(len(indices), target_remove - len(to_drop))
                if sample_count > 0:
                    to_drop.extend(random.sample(indices, sample_count))

        return to_drop[:target_remove]
