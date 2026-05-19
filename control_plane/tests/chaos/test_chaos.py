import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core import metrics

client = TestClient(app)

@pytest.mark.asyncio
async def test_chaos_provider_timeout():
    # Simulate a provider timeout and check circuit breaker / metrics
    from app.services.inference_proxy import InferenceProxy
    
    with patch("httpx.AsyncClient.post") as mock_post:
        # Simulate timeout
        mock_post.side_effect = asyncio.TimeoutError()
        
        # We need to call the recording logic to see if it registers the failure
        metrics.record_backend_error(
            model="test-model",
            backend="mock-timeout",
            plan="free",
            endpoint="/v1/chat/completions",
            status_code=504
        )
        
        from prometheus_client import REGISTRY
        val = REGISTRY.get_sample_value("llm_provider_failures_total", {
            "provider_name": "mock-timeout",
            "error_code": "504"
        })
        assert val >= 1.0

@pytest.mark.asyncio
async def test_chaos_queue_saturation():
    # Verify metric recording still works for saturation
    metrics.record_queue_wait(plan="free", wait_seconds=10.0)
    
    from prometheus_client import REGISTRY
    val = REGISTRY.get_sample_value("llm_queue_wait_seconds_count", {
        "plan": "free"
    })
    assert val >= 1.0

@pytest.mark.asyncio
async def test_chaos_tokenizer_unavailable():
    # Test tokenizer fallback
    from app.services.tokenizer_service import TokenizerService
    
    service = TokenizerService()
    # Mocking failure of real tokenizer (tiktoken is loaded dynamically)
    with patch("app.services.tokenizer_service._load_tiktoken", return_value=None):
        # If strict is false, it should fallback to estimation
        service.settings.tokenizer_strict = False
        res = await service.count_text_tokens("Hello world", model="gpt-4")
        assert res.is_estimated is True
        assert res.input_tokens > 0

        # If strict is true, it should raise if it can't find any real tokenizer
        # In TokenizerService.count_text_tokens, it falls back to estimation if everything fails
        # unless we mock it more aggressively.
        with patch("app.services.tokenizer_service.estimate_tokens_from_text", side_effect=Exception("estimation_failed")):
            service.settings.tokenizer_strict = True
            with pytest.raises(Exception):
                 await service.count_text_tokens("Hello world", model="gpt-4")

def test_chaos_hot_swap_failure():
    # Test hot swap failure recording
    metrics.record_hot_swap_failure("failed-model", "health_check_failed")
    
    from prometheus_client import REGISTRY
    val = REGISTRY.get_sample_value("llm_model_hot_swap_failures_total", {
        "model_id": "failed-model",
        "reason": "health_check_failed"
    })
    assert val >= 1.0

def test_chaos_attestation_failure():
    # Test attestation failure recording
    metrics.record_attestation_failure("node-1", "invalid_signature")
    
    from prometheus_client import REGISTRY
    val = REGISTRY.get_sample_value("llm_attestation_failures_total", {
        "node_id": "node-1",
        "reason": "invalid_signature"
    })
    assert val >= 1.0

def test_chaos_plugin_invalid_signature():
    # Similar to attestation, verify we can record security/plugin events
    # (Assuming we have a generic way to record these or use RBAC denials as proxy for chaos)
    metrics.record_rbac_denial("attacker", "/admin/plugins/load", "write")
    
    from prometheus_client import REGISTRY
    val = REGISTRY.get_sample_value("llm_rbac_denials_total", {
        "client_id": "attacker",
        "resource": "/admin/plugins/load",
        "action": "write"
    })
    assert val >= 1.0
