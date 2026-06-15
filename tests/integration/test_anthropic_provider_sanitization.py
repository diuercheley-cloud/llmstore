"""Tests for Anthropic provider sanitization — API key masking, prompt/response privacy."""

import json
import os
import re
import sys
from pathlib import Path

import pytest
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.schemas import ProviderCapabilities

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_LIB = PROJECT_ROOT / "scripts" / "lib"
if str(SCRIPT_LIB) not in sys.path:
    sys.path.insert(0, str(SCRIPT_LIB))
from anthropic_real_validator import mask_key, sanitize_log

ANTHROPIC_MASK_KEY = "sk-ant-test-key-1234567890abcdef"
ANTHROPIC_REALISTIC_KEY = "sk-ant-test-real-key-1234567890abcdef"
ANTHROPIC_REPORT_KEY = "sk-ant-real-key-12345678901234567890"
ANTHROPIC_REPORT_ENV_KEY = "test-anthropic-key"


def test_mask_api_key_method():
    provider = AnthropicProvider()
    masked = provider.mask_api_key(ANTHROPIC_MASK_KEY)
    assert masked == "sk-a****cdef"


def test_mask_api_key_short():
    provider = AnthropicProvider()
    masked = provider.mask_api_key("abc")
    assert masked == "****"


def test_mask_api_key_none():
    provider = AnthropicProvider()
    assert provider.mask_api_key(None) is None


def test_mask_api_key_empty():
    provider = AnthropicProvider()
    masked = provider.mask_api_key("")
    assert masked is None


@pytest.mark.asyncio
async def test_health_check_disabled_returns_sanitized():
    provider = AnthropicProvider()
    result = await provider.health_check()
    if not provider.enabled:
        assert result["error"] == "disabled"
        assert result.get("healthy") is None


@pytest.mark.asyncio
async def test_health_check_not_configured_returns_sanitized():
    os.environ["ANTHROPIC_API_KEY"] = ""
    os.environ["CLOUD_PROVIDERS_ENABLED"] = "true"
    os.environ["ANTHROPIC_PROVIDER_ENABLED"] = "true"
    os.environ["REAL_PROVIDER_VALIDATION_ENABLED"] = "true"
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider = AnthropicProvider()
    result = await provider.health_check()
    if not provider.configured:
        error = (result.get("error") or "").lower()
        assert "not configured" in error or "disabled" in error


KEY_LEAK_PATTERNS = [
    re.compile(r"sk-ant-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"sk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
]


@pytest.mark.asyncio
async def test_no_key_in_health_check_output():
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_REALISTIC_KEY
    os.environ["CLOUD_PROVIDERS_ENABLED"] = "true"
    os.environ["ANTHROPIC_PROVIDER_ENABLED"] = "true"
    os.environ["REAL_PROVIDER_VALIDATION_ENABLED"] = "true"
    from app.core.config import get_settings

    get_settings.cache_clear()
    provider = AnthropicProvider()
    result = await provider.health_check()
    sanitized = json.dumps(result)
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), f"Key leak in health_check: {pat}"


def test_no_key_in_capabilities():
    provider = AnthropicProvider()
    caps = provider.capabilities()
    assert isinstance(caps, ProviderCapabilities)
    sanitized = json.dumps(caps.model_dump())
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), "Key leak in capabilities"


def test_estimate_cost_sanitized():
    provider = AnthropicProvider()
    cost = provider.estimate_cost("claude-3-haiku-20240307", 100, 50)
    assert isinstance(cost, float)
    assert cost > 0


def test_log_prompt_enabled_default():
    provider = AnthropicProvider()
    val = provider.log_prompt_enabled()
    assert val is False


def test_store_response_enabled_default():
    provider = AnthropicProvider()
    val = provider.store_response_enabled()
    assert val is False


def test_max_cost_brl_default():
    provider = AnthropicProvider()
    val = provider.max_cost_brl()
    assert val == 2.00


def test_mask_key_function_strips():
    key = ANTHROPIC_REPORT_KEY
    masked = mask_key(key)
    assert masked != key
    assert "sk-a" in masked
    assert "****" in masked


def test_mask_key_keeps_prefix_suffix():
    key = ANTHROPIC_MASK_KEY
    masked = mask_key(key)
    assert masked == "sk-a****cdef"


def test_no_full_prompt_in_report_by_default(tmp_path):
    from anthropic_real_validator import AnthropicRealValidator

    args = type(
        "Args",
        (),
        {
            "dry_run": True,
            "real": True,
            "max_cost_brl": 2.0,
            "model": "claude-3-haiku-20240307",
            "output_dir": str(tmp_path),
        },
    )
    env = {
        "REAL_PROVIDER_VALIDATION_ENABLED": "true",
        "ANTHROPIC_PROVIDER_ENABLED": "true",
        "ANTHROPIC_API_KEY": ANTHROPIC_REPORT_ENV_KEY,
        "REAL_PROVIDER_LOG_PROMPTS": "false",
    }
    validator = AnthropicRealValidator(args, env)
    report = validator.run()
    report_str = json.dumps(report)
    assert "Responda apenas: OK" not in report_str


def test_sanitize_log_handles_non_string():
    assert sanitize_log(123) is not None
    assert sanitize_log(None) is not None
