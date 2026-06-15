import pytest
from app.core import metrics
from app.main import app
from app.services.platform_slo import PlatformSLOService
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_prometheus():
    # Helper to clear metrics before each test if needed,
    # but since REGISTRY is global, we just check increments.
    pass


def test_metrics_emission():
    # Record some metrics
    metrics.record_request_metrics(
        model="gpt-4",
        backend="openai",
        plan="premium",
        endpoint="/v1/chat/completions",
        status_code=200,
        latency_seconds=0.5,
        prompt_tokens=10,
        completion_tokens=20,
    )

    # Check if Prometheus can see them
    val = REGISTRY.get_sample_value(
        "llm_requests_total",
        {
            "model": "gpt-4",
            "backend": "openai",
            "plan": "premium",
            "endpoint": "/v1/chat/completions",
            "status_code": "200",
        },
    )
    assert val >= 1.0


def test_slo_report_status():
    service = PlatformSLOService()

    # Initial report should be ok (or 1.0 availability)
    report = service.get_slo_report()
    assert "api_availability" in report
    assert report["api_availability"]["status"] in ["ok", "warning", "critical"]


def test_provider_failure_increment():
    initial = (
        REGISTRY.get_sample_value(
            "llm_provider_failures_total", {"provider_name": "test-provider", "error_code": "500"}
        )
        or 0.0
    )

    metrics.record_backend_error(
        model="m1", backend="test-provider", plan="p1", endpoint="e1", status_code=500
    )

    final = REGISTRY.get_sample_value(
        "llm_provider_failures_total", {"provider_name": "test-provider", "error_code": "500"}
    )
    assert final == initial + 1.0


def test_routing_fallback_increment():
    initial = (
        REGISTRY.get_sample_value(
            "llm_routing_fallbacks_total", {"reason": "timeout", "model": "gpt-4"}
        )
        or 0.0
    )

    metrics.record_routing_fallback("timeout", "gpt-4")

    final = REGISTRY.get_sample_value(
        "llm_routing_fallbacks_total", {"reason": "timeout", "model": "gpt-4"}
    )
    assert final == initial + 1.0


def test_rbac_denial_increment():
    initial = (
        REGISTRY.get_sample_value(
            "llm_rbac_denials_total", {"client_id": "c1", "resource": "r1", "action": "a1"}
        )
        or 0.0
    )

    metrics.record_rbac_denial("c1", "r1", "a1")

    final = REGISTRY.get_sample_value(
        "llm_rbac_denials_total", {"client_id": "c1", "resource": "r1", "action": "a1"}
    )
    assert final == initial + 1.0


def test_hot_swap_failure_increment():
    initial = (
        REGISTRY.get_sample_value(
            "llm_model_hot_swap_failures_total", {"model_id": "m1", "reason": "oom"}
        )
        or 0.0
    )

    metrics.record_hot_swap_failure("m1", "oom")

    final = REGISTRY.get_sample_value(
        "llm_model_hot_swap_failures_total", {"model_id": "m1", "reason": "oom"}
    )
    assert final == initial + 1.0


def test_api_endpoints():
    response = client.get("/admin/observability/slo")
    assert response.status_code == 200
    assert "api_availability" in response.json()
    # Observability should NOT be deprecated
    assert "X-Deprecated-Endpoint" not in response.headers

    response = client.get("/admin/observability/platform-health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_deprecation_header():
    # /admin is marked as deprecated (unless it's observability/commercial/operations)
    # Using /admin/models/runtime as a known deprecated path prefix
    response = client.get("/admin/models/runtime/instances")
    # Even if it returns 404 or 401, the middleware should add the header if the path matches
    assert response.headers.get("X-Deprecated-Endpoint") == "true"
