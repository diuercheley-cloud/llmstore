import os
import pytest

from app.services.providers.registry import (
    _init_registry,
    get_all_provider_statuses,
    get_provider,
    get_providers,
    reload_registry,
)


@pytest.fixture(autouse=True)
def reset_registry():
    reload_registry()
    yield
    reload_registry()


class TestProviderRegistry:
    def test_registry_contains_expected_providers(self):
        providers = get_providers()
        ids = list(providers.keys())
        assert "local" in ids
        assert "lmstudio" in ids
        assert "openai" in ids
        assert "anthropic" in ids
        assert "deepseek" in ids
        assert "openrouter" in ids
        assert "gemini" in ids
        assert "bedrock" in ids
        assert "azure_openai" in ids
        assert "mistral" in ids
        assert "cohere" in ids
        assert "groq" in ids
        assert "together" in ids
        assert "perplexity" in ids
        assert "replicate" in ids
        assert "xai" in ids
        assert "fireworks" in ids
        assert "ai21" in ids

    def test_local_provider_enabled_and_configured(self):
        local = get_provider("local")
        assert local is not None
        assert local.enabled is True
        assert local.configured is True
        assert local.provider_id == "local"

    def test_cloud_providers_disabled_by_default(self):
        for pid in ("openai", "anthropic", "deepseek", "gemini", "bedrock", "azure_openai", "mistral", "cohere", "groq", "together", "perplexity", "replicate", "xai", "fireworks", "ai21"):
            p = get_provider(pid)
            assert p is not None
            assert p.configured is False, f"{pid} should be configured=false by default"

    def test_get_provider_returns_none_for_unknown(self):
        assert get_provider("nonexistent") is None

    def test_get_all_provider_statuses(self):
        statuses = get_all_provider_statuses()
        ids = [s.provider_id for s in statuses]
        assert "local" in ids
        for s in statuses:
            assert s.provider_id is not None
            assert s.provider_type is not None
            assert s.configured is not None

    def test_local_provider_capabilities(self):
        local = get_provider("local")
        caps = local.capabilities()
        assert caps.chat is True
        assert caps.streaming is True
        assert caps.embeddings is True
        assert caps.pricing_configured is False

    def test_openai_provider_capabilities(self):
        openai = get_provider("openai")
        caps = openai.capabilities()
        assert caps.chat is True
        assert caps.streaming is True
        assert caps.embeddings is True
        assert caps.tools is True
        assert caps.vision is True

    def test_anthropic_provider_capabilities(self):
        anthropic = get_provider("anthropic")
        caps = anthropic.capabilities()
        assert caps.chat is True
        assert caps.streaming is True
        assert caps.embeddings is False
        assert caps.vision is True

    def test_deepseek_provider_capabilities(self):
        deepseek = get_provider("deepseek")
        caps = deepseek.capabilities()
        assert caps.chat is True
        assert caps.embeddings is False
        assert caps.vision is False

    def test_local_estimate_cost_zero(self):
        local = get_provider("local")
        cost = local.estimate_cost("any-model", 100, 50)
        assert cost == 0.0

    def test_openai_estimate_cost(self):
        openai = get_provider("openai")
        # gpt-4o: $2.50/1M prompt, $10.00/1M completion
        cost = openai.estimate_cost("gpt-4o", 1_000_000, 0)
        assert cost == 2.50

    def test_anthropic_estimate_cost(self):
        anthropic = get_provider("anthropic")
        cost = anthropic.estimate_cost("claude-3-haiku", 1_000_000, 0)
        assert cost == 0.25

    def test_deepseek_estimate_cost(self):
        deepseek = get_provider("deepseek")
        cost = deepseek.estimate_cost("deepseek-chat", 1_000_000, 0)
        assert cost == 0.14

    def test_reload_registry_clears_cache(self):
        providers_before = get_providers()
        assert len(providers_before) > 0
        reload_registry()
        providers_after = get_providers()
        assert len(providers_after) > 0
        assert providers_after["local"].enabled is True
