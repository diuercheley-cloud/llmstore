# Owner: agent-platform
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Dict, List, Optional

from app.core.config import get_settings
from app.core.metrics import (
    LLM_AGENT_TELEMETRY_BACKPRESSURE_ACTIVE,
    LLM_AGENT_TELEMETRY_EXPORT_FAILURES_TOTAL,
    LLM_AGENT_TELEMETRY_QUEUE_DEPTH,
    LLM_AGENT_TELEMETRY_SPANS_DROPPED_TOTAL,
)
from app.services.agents.telemetry.leaky_bucket import LeakyBucketManager
from app.services.agents.telemetry.span_priority import (
    SpanPriority,
    classify_span_priority,
    should_never_drop,
)
from app.services.agents.telemetry.span_sampler import SpanSampler

logger = logging.getLogger(__name__)


class TelemetryBackpressure:
    def __init__(
        self,
        max_queue_size: int = 1000,
        drain_batch_size: int = 50,
        drain_interval_seconds: float = 1.0,
    ):
        self.max_queue_size = max_queue_size
        self.drain_batch_size = drain_batch_size
        self.drain_interval_seconds = drain_interval_seconds

        self._queue: deque = deque()
        self._lock = threading.Lock()
        self._drain_thread: Optional[threading.Thread] = None
        self._running = False

        self.bucket_manager = LeakyBucketManager()
        self.sampler = SpanSampler()
        self._exporters: List[Callable[[Dict], Optional[Dict]]] = []

        self._drop_count: int = 0
        self._export_failure_count: int = 0

    def register_exporter(self, exporter: Callable[[Dict], Optional[Dict]]) -> None:
        self._exporters.append(exporter)

    def enqueue(
        self,
        span: Dict,
        tenant_id: str = "default",
        agent_id: str = "unknown",
    ) -> bool:
        settings = get_settings()
        if not settings.agent_telemetry_backpressure_enabled:
            return True

        span_type = span.get("type", "")
        priority = classify_span_priority(span_type)

        if not self.bucket_manager.check_quota(tenant_id, agent_id, span_type):
            if should_never_drop(priority):
                with self._lock:
                    self._queue.append(span)
                    self._update_metrics(tenant_id, agent_id)
                return True

            if priority == SpanPriority.DEBUG and settings.agent_telemetry_drop_debug_spans_enabled:
                LLM_AGENT_TELEMETRY_SPANS_DROPPED_TOTAL.labels(
                    tenant_id=tenant_id, agent_id=agent_id,
                    priority=priority.name.lower(), reason="leaky_bucket",
                ).inc()
                self._drop_count += 1
                return False

            self._queue.append(span)
            return True

        with self._lock:
            if len(self._queue) >= self.max_queue_size:
                self._drain_to_make_room(tenant_id, agent_id)
                self._queue.append(span)
                self._update_metrics(tenant_id, agent_id)
                return True

            self._queue.append(span)
            self._update_metrics(tenant_id, agent_id)

        return True

    def _drain_to_make_room(
        self,
        tenant_id: str,
        agent_id: str,
    ) -> int:
        target_remove = len(self._queue) - self.max_queue_size + 1
        if target_remove <= 0:
            return 0

        to_drop = self.sampler.select_spans_to_drop(
            list(self._queue), target_remove
        )
        for idx in sorted(to_drop, reverse=True):
            span = self._queue[idx]
            span_priority = classify_span_priority(span.get("type", ""))
            LLM_AGENT_TELEMETRY_SPANS_DROPPED_TOTAL.labels(
                tenant_id=tenant_id, agent_id=agent_id,
                priority=span_priority.name.lower(), reason="queue_full",
            ).inc()
            del self._queue[idx]

        self._drop_count += len(to_drop)
        return len(to_drop)

    def _update_metrics(self, tenant_id: str, agent_id: str) -> None:
        priority_counts: Dict[str, int] = defaultdict(int)
        for s in self._queue:
            p = classify_span_priority(s.get("type", ""))
            priority_counts[p.name.lower()] += 1

        for pname, count in priority_counts.items():
            LLM_AGENT_TELEMETRY_QUEUE_DEPTH.labels(
                tenant_id=tenant_id, agent_id=agent_id, priority=pname,
            ).set(count)

        is_active = 1 if len(self._queue) > self.max_queue_size * 0.8 else 0
        LLM_AGENT_TELEMETRY_BACKPRESSURE_ACTIVE.labels(
            tenant_id=tenant_id, agent_id=agent_id,
        ).set(is_active)

    def start_drain_loop(self) -> None:
        if self._running:
            return
        self._running = True
        self._drain_thread = threading.Thread(
            target=self._drain_loop, daemon=True, name="telemetry-drain"
        )
        self._drain_thread.start()
        logger.info("Telemetry drain loop started.")

    def stop_drain_loop(self) -> None:
        self._running = False
        logger.info("Telemetry drain loop stopped.")

    def _drain_loop(self) -> None:
        while self._running:
            try:
                self._flush_batch()
            except Exception:
                logger.exception("Error in telemetry drain loop.")
            time.sleep(self.drain_interval_seconds)

    def _flush_batch(self) -> int:
        batch: List[Dict] = []
        with self._lock:
            for _ in range(min(self.drain_batch_size, len(self._queue))):
                batch.append(self._queue.popleft())
            self._update_metrics("default", "unknown")

        if not batch:
            return 0

        settings = get_settings()
        for span in batch:
            exported = self._export_span(span)
            if not exported:
                if settings.agent_telemetry_strict_export:
                    logger.warning(
                        "Strict export: span %s failed to export.",
                        span.get("span_id", span.get("id", "unknown")),
                    )
            if exported is not None and not exported:
                LLM_AGENT_TELEMETRY_EXPORT_FAILURES_TOTAL.labels(
                    tenant_id="default", agent_id="unknown", exporter="default",
                ).inc()
                self._export_failure_count += 1

        return len(batch)

    def _export_span(self, span: Dict) -> Optional[bool]:
        if not self._exporters:
            return None
        for exporter in self._exporters:
            try:
                result = exporter(span)
                if result is False:
                    return False
            except Exception:
                logger.exception("Exporter failed for span %s", span.get("id"))
                return False
        return True

    def enqueue_span(
        self,
        span: Dict,
        tenant_id: str = "default",
        agent_id: str = "unknown",
    ) -> bool:
        return self.enqueue(span, tenant_id, agent_id)

    @property
    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)

    @property
    def drop_count(self) -> int:
        return self._drop_count

    @property
    def export_failure_count(self) -> int:
        return self._export_failure_count

    def flush_all(self) -> int:
        total = 0
        while self.queue_size > 0:
            total += self._flush_batch()
        return total
