from unittest.mock import MagicMock, patch

import pytest

from scripts.llm_harness.metrics import MetricsManager
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.queue import InMemoryQueue
from scripts.llm_harness.tracing import Tracer
from scripts.llm_harness.webhooks import WebhookManager


def test_metrics_manager():
    m = MetricsManager()
    m.start_run()
    m.record_llm_call(tokens=100, prompt_tokens=60, completion_tokens=40, cost=0.01)
    m.record_tool_call(cached=True)
    m.record_tool_call(cached=False)
    m.end_run(success=True)
    
    data = m.to_dict()
    assert data["runs_total"] == 1
    assert data["runs_failed"] == 0
    assert data["llm_calls_total"] == 1
    assert data["tool_calls_total"] == 2
    assert data["tokens_total"] == 100
    assert data["cache_hits"] == 1
    assert data["cache_misses"] == 1
    assert data["duration_ms"] >= 0

def test_tracer():
    t = Tracer()
    trace_id = t.get_trace_id()
    assert trace_id is not None
    
    span_id = t.start_span("test-span")
    assert span_id in t.spans
    t.end_span(span_id)
    assert span_id not in t.spans

@pytest.mark.asyncio
async def test_webhook_manager():
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        
        w = WebhookManager(url="http://example.com/webhook")
        await w.send_event("run.started", {"api_key": "secret-123", "data": "info"})
        
        assert mock_post.called
        # Check sanitization
        args, kwargs = mock_post.call_args
        sent_data = kwargs["json"]
        assert sent_data["payload"]["data"] == "info"
        assert "api_key" not in sent_data["payload"]

def test_policy_rate_limiting():
    config = {"max_llm_calls_per_minute": 2}
    p = PolicyEngine(config=config)
    
    # First two calls should be allowed
    assert p.check_usage(tokens=0, cost=0.0) is True
    p.record_llm_call()
    assert p.check_usage(tokens=0, cost=0.0) is True
    p.record_llm_call()
    
    # Third call should be blocked
    assert p.check_usage(tokens=0, cost=0.0) is False

@pytest.mark.asyncio
async def test_in_memory_queue():
    q = InMemoryQueue()
    await q.push({"id": 1})
    await q.push({"id": 2})
    
    t1 = await q.pop()
    t2 = await q.pop()
    
    assert t1["id"] == 1
    assert t2["id"] == 2
