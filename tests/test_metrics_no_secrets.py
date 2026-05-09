from prometheus_client import generate_latest

from app.core.metrics import record_request_metrics


def test_metrics_do_not_expose_secrets(monkeypatch):
    admin_token = "sk-local-" + "test-admin-token"
    openai_api_key = "sk-live-" + "secret-value"
    monkeypatch.setenv("ADMIN_TOKEN", admin_token)
    monkeypatch.setenv("OPENAI_API_KEY", openai_api_key)

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

    assert admin_token not in metrics_text
    assert openai_api_key not in metrics_text
    assert "OPENAI_API_KEY" not in metrics_text
