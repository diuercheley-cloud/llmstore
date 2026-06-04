import pytest
from app.core.config import Settings
from app.core.runtime_security import is_strong_admin_token, validate_runtime_security


def test_is_strong_admin_token_accepts_mixed_long_token():
    assert is_strong_admin_token("Admin-Token-2026_local-secure")


def test_is_strong_admin_token_rejects_default_or_weak_values():
    assert not is_strong_admin_token("change-this-admin-token")
    assert not is_strong_admin_token("short-token")
    assert not is_strong_admin_token("alllowercaseandverylongtoken")


def test_validate_runtime_security_blocks_public_exposure_with_weak_admin_token():
    settings = Settings.model_construct(
        project_name="test",
        debug=False,
        log_level="INFO",
        control_plane_host="0.0.0.0",
        control_plane_port=8080,
        admin_token="change-this-admin-token",
        cors_allow_origins="",
        public_exposure=True,
        database_url="postgresql://example",
        redis_url="redis://example",
        data_plane_base_url="http://example",
        ollama_base_url="http://example",
        data_plane_timeout_seconds=10,
        request_timeout_seconds=10,
        queue_timeout_seconds=10,
        max_concurrent_generations=1,
        max_queue_size=1,
        async_job_queue_name="jobs",
        async_worker_block_seconds=1,
        max_context_tokens=1024,
        max_input_tokens=1024,
        default_max_tokens=128,
        max_completion_tokens=256,
        default_temperature=0.7,
        max_temperature=1.0,
        default_top_p=0.9,
        max_top_p=1.0,
        retry_attempts=1,
        retry_backoff_seconds=0.1,
        circuit_breaker_failure_threshold=1,
        circuit_breaker_recovery_seconds=1,
        response_cache_enabled=True,
        response_cache_ttl_seconds=60,
        semantic_cache_enabled=False,
        billing_invoice_day=1,
        billing_due_days=7,
        billing_suspend_after_days=15,
        demo_client_name="demo-client",
        demo_rate_limit_per_minute=5,
        demo_daily_token_quota=1000,
        demo_monthly_token_quota=10000,
        model_id="demo-model",
        model_file="demo.gguf",
    )

    with pytest.raises(RuntimeError) as exc_info:
        validate_runtime_security(settings)
    assert "PUBLIC_EXPOSURE=true" in str(exc_info.value)
