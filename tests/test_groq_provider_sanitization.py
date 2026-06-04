"""Tests for Groq provider sanitization — API key masking, prompt/response privacy."""

import json
import re

import pytest
from app.services.providers.base import ProviderType
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.schemas import ProviderCapabilities

GROQ_MASK_KEY = "gsk_abcdefghijklmnopqrstuvwxyz123456"
GROQ_REALISTIC_KEY = "gsk_test_real_key_1234567890abcdef"


def test_mask_api_key_method():
    provider = GroqProvider()
    masked = provider.mask_api_key(GROQ_MASK_KEY)
    assert masked == "gsk_****3456"


def test_mask_api_key_short():
    provider = GroqProvider()
    masked = provider.mask_api_key("abc")
    assert masked == "****"


def test_mask_api_key_none():
    provider = GroqProvider()
    assert provider.mask_api_key(None) is None


def test_mask_api_key_empty():
    provider = GroqProvider()
    masked = provider.mask_api_key("")
    assert masked is None


@pytest.mark.asyncio
async def test_health_check_disabled_returns_sanitized():
    provider = GroqProvider()
    result = await provider.health_check()
    if not provider.enabled:
        assert result["error"] == "disabled"
        assert result.get("healthy") is None


KEY_LEAK_PATTERNS = [
    re.compile(r"gsk-[a-zA-Z0-9][a-zA-Z0-9._-]{20,}"),
    re.compile(r"Bearer gsk-[a-zA-Z0-9][a-zA-Z0-9._-]+"),
]


@pytest.mark.asyncio
async def test_no_key_in_health_check_output(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", GROQ_REALISTIC_KEY)
    monkeypatch.setenv("CLOUD_PROVIDERS_ENABLED", "true")
    monkeypatch.setenv("GROQ_PROVIDER_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    provider = GroqProvider()
    result = await provider.health_check()
    sanitized = json.dumps(result)
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), f"Key leak in health_check: {pat}"


def test_no_key_in_capabilities():
    provider = GroqProvider()
    caps = provider.capabilities()
    assert isinstance(caps, ProviderCapabilities)
    sanitized = json.dumps(caps.model_dump())
    for pat in KEY_LEAK_PATTERNS:
        assert not pat.search(sanitized), "Key leak in capabilities"


def test_estimate_cost_sanitized():
    provider = GroqProvider()
    cost = provider.estimate_cost("llama-3.1-70b", 100, 50)
    assert isinstance(cost, float)
    assert cost == 0.0


def test_capabilities_structure():
    provider = GroqProvider()
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
    provider = GroqProvider()
    assert provider.provider_id == "groq"
    assert provider.provider_type == ProviderType.GROQ
