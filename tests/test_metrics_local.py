from app.core.metrics import (
    record_backend_error,
    record_cache_result,
    record_inference_latency,
    record_model_error,
    record_queue_wait,
    record_request_metrics,
)
from prometheus_client import generate_latest


def test_local_metrics_expose_expected_families():
    record_request_metrics(
        model="unit-test-model",
        backend="unit-backend",
        plan="basic",
        endpoint="/v1/chat/completions",
        status_code=200,
        latency_seconds=0.123,
        prompt_tokens=12,
        completion_tokens=34,
    )
    record_inference_latency(
        model="unit-test-model",
        backend="unit-backend",
        plan="basic",
        endpoint="/v1/chat/completions",
        status_code=200,
        latency_seconds=0.045,
    )
    record_queue_wait(plan="basic", wait_seconds=0.02)
    record_cache_result(
        hit=True,
        model="unit-test-model",
        backend="cache",
        plan="basic",
        endpoint="/v1/chat/completions",
    )
    record_cache_result(
        hit=False,
        model="unit-test-model",
        backend="cache",
        plan="basic",
        endpoint="/v1/chat/completions",
    )
    record_backend_error(
        model="unit-test-model",
        backend="unit-backend",
        plan="basic",
        endpoint="/v1/chat/completions",
        status_code=503,
    )
    record_model_error(
        model="unit-test-model",
        backend="unit-backend",
        plan="basic",
        endpoint="/v1/chat/completions",
        status_code=400,
    )

    metrics_text = generate_latest().decode("utf-8")

    assert "requests_total" in metrics_text
    assert "request_latency_seconds" in metrics_text
    assert "tokens_prompt_total" in metrics_text
    assert "tokens_completion_total" in metrics_text
    assert "tokens_total" in metrics_text
    assert "inference_latency_seconds" in metrics_text
    assert "queue_wait_seconds" in metrics_text
    assert "cache_hits_total" in metrics_text
    assert "cache_misses_total" in metrics_text
    assert "backend_errors_total" in metrics_text
    assert "model_errors_total" in metrics_text
