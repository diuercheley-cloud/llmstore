from prometheus_client import generate_latest

from app.core.metrics import record_request_metrics


def test_metrics_do_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "sk-local-test-admin-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-live-secret-value")

    record_request_metrics(
        model="public-model",
        backend="public-backend",
        plan="free",
        endpoint="/v1/chat/completions",
        status_code=200,
        latency_seconds=0.01,
        prompt_tokens=1,
        completion_tokens=2,
    )

    metrics_text = generate_latest().decode("utf-8")

    assert "sk-local-test-admin-token" not in metrics_text
    assert "sk-live-secret-value" not in metrics_text
    assert "OPENAI_API_KEY" not in metrics_text
