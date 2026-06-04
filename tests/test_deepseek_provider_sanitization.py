"""Tests for DeepSeek provider sanitization — API key masking, prompt/response privacy."""

import json
import os
import re
import sys
from pathlib import Path

import pytest
from app.services.providers.deepseek_provider import DeepSeekProvider
from app.services.providers.schemas import ProviderCapabilities

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_LIB = PROJECT_ROOT / "scripts" / "lib"
if str(SCRIPT_LIB) not in sys.path:
    sys.path.insert(0, str(SCRIPT_LIB))
from deepseek_real_validator import mask_key, sanitize_log

DEEPSEEK_MASK_KEY = "sk-" "deepseek-test-key-1234567890"
DEEPSEEK_REALISTIC_KEY = "sk-" "test-real-key-1234567890abcdef"
DEEPSEEK_REPORT_KEY = "sk-" "deepseek-real-key-12345678901234567890"
DEEPSEEK_REPORT_ENV_KEY = "test-deepseek-key"


def test_mask_api_key_method():
    provider = DeepSeekProvider()
    masked = provider.mask_api_key(DEEPSEEK_MASK_KEY)
    assert masked == "sk-d****7890"


def test_mask_api_key_short():
    provider = DeepSeekProvider()
    masked = provider.mask_api_key("abc")
    assert masked == "****"


def test_mask_api_key_none():
    provider = DeepSeekProvider()
    assert provider.mask_api_key(None) is None


def test_mask_api_key_empty():
    provider = DeepSeekProvider()
    masked = provider.mask_api_key("")
    assert masked is None


@pytest.mark.asyncio
async def test_health_check_disabled_returns_sanitized():
    provider = DeepSeekProvider()
    result = await provider.health_check()
    if not provider.enabled:
        assert result["error"] == "disabled"
        assert result.get("healthy") is None


KEY_LEAK_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"Bearer sk-[a-zA-Z0-9][a-zA-Z0-9._-]+"),
]


@pytest.mark.asyncio
async def test_no_key_in_health_check_output():
    os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_REALISTIC_KEY
    os.environ["CLOUD_PROVIDERS_ENABLED"] = "true"
    os.environ["DEEPSEEK_PROVIDER_ENABLED"] = "true"
    os.environ["REAL_PROVIDER_VALIDATION_ENABLED"] = "true"
    from app.core.config import get_settings
    get_settings.cache_clear()
    provider = DeepSeekProvider()
    result = await provider.health_check()
    sanitized = json.dumps(result)
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), f"Key leak in health_check: {pat}"


def test_no_key_in_capabilities():
    provider = DeepSeekProvider()
    caps = provider.capabilities()
    assert isinstance(caps, ProviderCapabilities)
    sanitized = json.dumps(caps.model_dump())
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), "Key leak in capabilities"


def test_estimate_cost_sanitized():
    provider = DeepSeekProvider()
    cost = provider.estimate_cost("deepseek-chat", 100, 50)
    assert isinstance(cost, float)
    assert cost > 0


def test_log_prompt_enabled_default():
    provider = DeepSeekProvider()
    val = provider.log_prompt_enabled()
    assert val is False


def test_store_response_enabled_default():
    provider = DeepSeekProvider()
    val = provider.store_response_enabled()
    assert val is False


def test_max_cost_brl_default():
    provider = DeepSeekProvider()
    val = provider.max_cost_brl()
    assert val == 2.00


def test_mask_key_function_strips():
    key = DEEPSEEK_REPORT_KEY
    masked = mask_key(key)
    assert masked != key
    assert "sk-d" in masked
    assert "****" in masked


def test_mask_key_keeps_prefix_suffix():
    key = DEEPSEEK_MASK_KEY
    masked = mask_key(key)
    assert masked == "sk-d****7890"


def test_no_full_prompt_in_report_by_default(tmp_path):
    from deepseek_real_validator import DeepSeekRealValidator
    args = type("Args", (), {"dry_run": True, "real": True, "max_cost_brl": 2.0, "model": "deepseek-chat",
                             "output_dir": str(tmp_path)})
    env = {
        "REAL_PROVIDER_VALIDATION_ENABLED": "true",
        "DEEPSEEK_PROVIDER_ENABLED": "true",
        "DEEPSEEK_API_KEY": DEEPSEEK_REPORT_ENV_KEY,
        "REAL_PROVIDER_LOG_PROMPTS": "false",
    }
    validator = DeepSeekRealValidator(args, env)
    report = validator.run()
    report_str = json.dumps(report)
    assert "Responda apenas: OK" not in report_str


def test_sanitize_log_handles_non_string():
    assert sanitize_log(123) is not None
    assert sanitize_log(None) is not None


def test_responses_raises_not_implemented():
    provider = DeepSeekProvider()
    import pytest
    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(provider.responses({"model": "deepseek-chat"}))


def test_embeddings_raises_not_implemented():
    provider = DeepSeekProvider()
    import pytest
    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(provider.embeddings({"model": "deepseek-chat", "input": "test"}))


def test_capabilities_responses_false():
    provider = DeepSeekProvider()
    caps = provider.capabilities()
    assert caps.responses is False


def test_capabilities_embeddings_false():
    provider = DeepSeekProvider()
    caps = provider.capabilities()
    assert caps.embeddings is False


def test_capabilities_chat_true():
    provider = DeepSeekProvider()
    caps = provider.capabilities()
    assert caps.chat is True


def test_capabilities_streaming_true():
    provider = DeepSeekProvider()
    caps = provider.capabilities()
    assert caps.streaming is True
