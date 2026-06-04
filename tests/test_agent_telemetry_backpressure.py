import logging
import time
from unittest.mock import MagicMock, patch

import pytest
from app.services.agents.telemetry.backpressure import TelemetryBackpressure
from app.services.agents.telemetry.leaky_bucket import LeakyBucket, LeakyBucketManager
from app.services.agents.telemetry.span_priority import (
    SpanPriority,
    can_drop,
    classify_span_priority,
    should_never_drop,
)
from app.services.agents.telemetry.span_sampler import SpanSampler

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def reset_settings():
    with patch("app.services.agents.telemetry.backpressure.get_settings") as mock:
        settings = MagicMock()
        settings.agent_telemetry_backpressure_enabled = True
        settings.agent_telemetry_drop_debug_spans_enabled = True
        settings.agent_telemetry_strict_export = False
        mock.return_value = settings
        yield mock


def make_span(span_type: str, span_id: str | None = None) -> dict:
    return {
        "id": span_id or f"span-{span_type}-{time.time_ns()}",
        "type": span_type,
        "name": f"test.{span_type}",
    }


class TestSpanPriority:
    def test_classify_critical(self):
        for t in ("error", "policy_denial", "approval", "security"):
            assert classify_span_priority(t) == SpanPriority.CRITICAL

    def test_classify_high(self):
        for t in ("run_start", "run_end", "tool_call"):
            assert classify_span_priority(t) == SpanPriority.HIGH

    def test_classify_normal(self):
        for t in ("model_call", "memory_call"):
            assert classify_span_priority(t) == SpanPriority.NORMAL

    def test_classify_debug(self):
        for t in ("token_usage", "debug", "llm_trace_debug"):
            assert classify_span_priority(t) == SpanPriority.DEBUG

    def test_classify_unknown_defaults_to_normal(self):
        assert classify_span_priority("unknown_type") == SpanPriority.NORMAL

    def test_should_never_drop_critical(self):
        assert should_never_drop(SpanPriority.CRITICAL)

    def test_can_drop_debug(self):
        assert can_drop(SpanPriority.DEBUG)
        assert can_drop(SpanPriority.NORMAL)

    def test_cannot_drop_critical(self):
        assert not can_drop(SpanPriority.CRITICAL)
        assert not can_drop(SpanPriority.HIGH)


class TestLeakyBucket:
    def test_try_consume_within_capacity(self):
        bucket = LeakyBucket(capacity=10, leak_rate=100)
        for _ in range(10):
            assert bucket.try_consume()

    def test_try_consume_exceeds_capacity(self):
        bucket = LeakyBucket(capacity=3, leak_rate=0.0)
        assert bucket.try_consume()
        assert bucket.try_consume()
        assert bucket.try_consume()
        assert not bucket.try_consume()

    def test_leaky_bucket_recovers(self):
        bucket = LeakyBucket(capacity=2, leak_rate=10.0)
        assert bucket.try_consume()
        assert bucket.try_consume()
        assert not bucket.try_consume()
        time.sleep(0.3)
        assert bucket.try_consume()

    def test_fill_ratio(self):
        bucket = LeakyBucket(capacity=10, leak_rate=0.0)
        bucket.try_consume(5)
        ratio = bucket.fill_ratio
        assert 0.49 < ratio < 0.51

    def test_reset(self):
        bucket = LeakyBucket(capacity=2, leak_rate=0.0)
        bucket.try_consume()
        bucket.try_consume()
        assert not bucket.try_consume()
        bucket.reset()
        assert bucket.try_consume()


class TestLeakyBucketManager:
    def test_get_or_create(self):
        mgr = LeakyBucketManager()
        b1 = mgr.get_or_create("key1", 10, 1.0)
        b2 = mgr.get_or_create("key1", 10, 1.0)
        assert b1 is b2

    def test_check_quota(self):
        mgr = LeakyBucketManager()
        assert mgr.check_quota("tenant1", "agent1", "model_call")
        assert mgr.check_quota("tenant1", "agent1", "model_call")

    def test_reset_key(self):
        mgr = LeakyBucketManager()
        bucket = mgr.get_or_create("test:key", 2, 0.0)
        bucket.try_consume()
        bucket.try_consume()
        assert not bucket.try_consume()
        mgr.reset_key("test:key")
        assert bucket.try_consume()

    def test_reset_all(self):
        mgr = LeakyBucketManager()
        b1 = mgr.get_or_create("a", 2, 0.0)
        b2 = mgr.get_or_create("b", 2, 0.0)
        b1.try_consume(2)
        b2.try_consume(2)
        assert not b1.try_consume()
        assert not b2.try_consume()
        mgr.reset_all()
        assert b1.try_consume()
        assert b2.try_consume()


class TestSpanSampler:
    def test_should_sample_critical_always(self):
        sampler = SpanSampler()
        assert sampler.should_sample("error")

    def test_should_sample_debug_rarely(self):
        sampler = SpanSampler()
        results = [sampler.should_sample("debug") for _ in range(100)]
        true_count = sum(1 for r in results if r)
        assert true_count < 50

    def test_set_sample_rate(self):
        sampler = SpanSampler()
        sampler.set_sample_rate(SpanPriority.DEBUG, 1.0)
        assert sampler.should_sample("debug")

    def test_select_spans_to_drop_drops_debug_first(self):
        sampler = SpanSampler()
        queue = [
            make_span("error"),
            make_span("debug"),
            make_span("debug"),
            make_span("model_call"),
        ]
        to_drop = sampler.select_spans_to_drop(queue, 2)
        assert len(to_drop) == 2
        dropped_types = [queue[i]["type"] for i in to_drop]
        assert all(t == "debug" or t == "model_call" for t in dropped_types)

    def test_critical_not_in_drop_candidates(self):
        sampler = SpanSampler()
        queue = [
            make_span("error"),
            make_span("security"),
            make_span("approval"),
            make_span("debug"),
        ]
        to_drop = sampler.select_spans_to_drop(queue, 10)
        dropped_types = {queue[i]["type"] for i in to_drop}
        assert "error" not in dropped_types
        assert "security" not in dropped_types
        assert "approval" not in dropped_types
        assert "debug" in dropped_types


class TestTelemetryBackpressure:
    def test_enqueue_accepts_normal_span(self, reset_settings):
        bp = TelemetryBackpressure(max_queue_size=10)
        result = bp.enqueue(make_span("model_call"))
        assert result is True
        assert bp.queue_size == 1

    def test_queue_full_drops_debug(self, reset_settings):
        bp = TelemetryBackpressure(max_queue_size=3)
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("debug"))
        assert bp.queue_size <= 3

    def test_critical_not_dropped(self, reset_settings):
        bp = TelemetryBackpressure(max_queue_size=2)
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("error"))
        assert bp.queue_size == 2
        assert bp.bucket_manager is not None
        has_error = any(s.get("type") == "error" for s in list(bp._queue))
        assert has_error, "Critical error span must be in the queue"

    def test_slow_exporter_does_not_block(self, reset_settings):
        bp = TelemetryBackpressure(max_queue_size=100)

        def slow_exporter(span):
            time.sleep(0.5)
            return True

        bp.register_exporter(slow_exporter)
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        assert bp.queue_size == 3

    def test_drop_metrics_increment(self, reset_settings):
        bp = TelemetryBackpressure(max_queue_size=3)
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("model_call"))
        bp.enqueue(make_span("debug"))
        assert bp.drop_count >= 1

    def test_strict_mode_logs_warning(self, reset_settings):
        with patch("app.services.agents.telemetry.backpressure.get_settings") as mock:
            settings = MagicMock()
            settings.agent_telemetry_backpressure_enabled = True
            settings.agent_telemetry_drop_debug_spans_enabled = True
            settings.agent_telemetry_strict_export = True
            mock.return_value = settings

            bp = TelemetryBackpressure(max_queue_size=10)
            results = []

            def failing_exporter(span):
                return False

            bp.register_exporter(failing_exporter)
            bp.enqueue(make_span("error"))
            result = bp._export_span(make_span("error"))
            results.append(result)
            assert any(r is False for r in results if r is not None)

    def test_drain_loop_drains_queue(self, reset_settings):
        bp = TelemetryBackpressure(
            max_queue_size=100, drain_batch_size=10, drain_interval_seconds=0.05
        )

        def fast_exporter(span):
            return True

        bp.register_exporter(fast_exporter)
        for _ in range(20):
            bp.enqueue(make_span("model_call"))
        assert bp.queue_size == 20
        bp._flush_batch()
        assert bp.queue_size == 10

    def test_flush_all_empties_queue(self, reset_settings):
        bp = TelemetryBackpressure(max_queue_size=100, drain_batch_size=50)

        def fast_exporter(span):
            return True

        bp.register_exporter(fast_exporter)
        for _ in range(30):
            bp.enqueue(make_span("model_call"))
        assert bp.queue_size == 30
        total = bp.flush_all()
        assert total == 30
        assert bp.queue_size == 0

    def test_backpressure_disabled_passthrough(self, reset_settings):
        with patch("app.services.agents.telemetry.backpressure.get_settings") as mock:
            settings = MagicMock()
            settings.agent_telemetry_backpressure_enabled = False
            settings.agent_telemetry_drop_debug_spans_enabled = True
            settings.agent_telemetry_strict_export = False
            mock.return_value = settings

            bp = TelemetryBackpressure(max_queue_size=2)
            for _ in range(10):
                bp.enqueue(make_span("debug"))
            assert bp.queue_size == 0
