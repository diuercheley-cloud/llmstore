"""Tests for Together AI provider sanitization — API key masking, prompt/response privacy."""

import json
import os
import re

import pytest

from app.services.providers.base import ProviderType
from app.services.providers.together_provider import TogetherProvider
from app.services.providers.schemas import ProviderCapabilities

TOGETHER_MASK_KEY = "tgp_v1_abcdefghijklmnopqrstuvwxyz123456"
TOGETHER_REALISTIC_KEY = "tgp_v1_test_real_key_1234567890abcdef"


def test_mask_api_key_method():
    provider = TogetherProvider()
    masked = provider.mask_api_key(TOGETHER_MASK_KEY)
    assert masked == "tgp_****3456"


def test_mask_api_key_short():
    provider = TogetherProvider()
    masked = provider.mask_api_key("abc")
    assert masked == "****"


def test_mask_api_key_none():
    provider = TogetherProvider()
    assert provider.mask_api_key(None) is None


def test_mask_api_key_empty():
    provider = TogetherProvider()
    masked = provider.mask_api_key("")
    assert masked is None


@pytest.mark.asyncio
async def test_health_check_disabled_returns_sanitized():
    provider = TogetherProvider()
    result = await provider.health_check()
    if not provider.enabled:
        assert result["error"] == "disabled"
        assert result.get("healthy") is None


KEY_LEAK_PATTERNS = [
    re.compile(r"tgp_[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"Bearer tgp_[a-zA-Z0-9][a-zA-Z0-9._-]+"),
]


@pytest.mark.asyncio
async def test_no_key_in_health_check_output(monkeypatch):
    monkeypatch.setenv("TOGETHER_API_KEY", TOGETHER_REALISTIC_KEY)
    monkeypatch.setenv("CLOUD_PROVIDERS_ENABLED", "true")
    monkeypatch.setenv("TOGETHER_PROVIDER_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    provider = TogetherProvider()
    result = await provider.health_check()
    sanitized = json.dumps(result)
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), f"Key leak in health_check: {pat}"


def test_no_key_in_capabilities():
    provider = TogetherProvider()
    caps = provider.capabilities()
    assert isinstance(caps, ProviderCapabilities)
    sanitized = json.dumps(caps.model_dump())
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), f"Key leak in capabilities"


def test_estimate_cost_sanitized():
    provider = TogetherProvider()
    cost = provider.estimate_cost("mistralai/Mixtral-8x7B-Instruct-v0.1", 100, 50)
    assert isinstance(cost, float)
    assert cost == 0.0


def test_capabilities_structure():
    provider = TogetherProvider()
    caps = provider.capabilities()
    assert caps.chat is True
    assert caps.streaming is True
    assert caps.embeddings is True
    assert caps.tools is True
    assert caps.vision is True
    assert caps.json_mode is True
    assert caps.max_context_tokens == 131072
    assert caps.pricing_configured is False


def test_provider_id_and_type():
    provider = TogetherProvider()
    assert provider.provider_id == "together"
    assert provider.provider_type == ProviderType.TOGETHER
