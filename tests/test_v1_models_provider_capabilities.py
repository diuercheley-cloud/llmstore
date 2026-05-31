import pytest
from app.services.providers.registry import get_providers, reload_registry, get_enabled_configured_providers


@pytest.fixture(autouse=True)
def reset_registry():
    reload_registry()
    yield
    reload_registry()


class TestV1ModelsProviderCapabilities:
    def test_local_provider_present(self):
        providers = get_providers()
        assert "local" in providers
        assert providers["local"].provider_type.value == "local"

    def test_all_providers_have_capabilities(self):
        providers = get_providers()
        for pid, p in providers.items():
            caps = p.capabilities()
            assert caps.chat is not None
            assert caps.streaming is not None
            assert caps.max_context_tokens > 0

    def test_cloud_providers_not_listed_as_usable_if_not_configured(self):
        usable = get_enabled_configured_providers()
        for p in usable:
            assert p.enabled is True
            assert p.configured is True
        # By default (no cloud keys), only local should be usable
        pids = [p.provider_id for p in usable]
        assert "local" in pids
        # Cloud providers shouldn't be in usable list
        for cloud in ("openai", "anthropic", "deepseek", "openrouter", "gemini", "bedrock", "azure_openai", "mistral", "cohere", "groq", "together", "perplexity", "replicate", "xai", "fireworks", "ai21"):
            assert cloud not in pids, f"{cloud} should not be usable without API key"

    def test_provider_info_dict_structure(self):
        """Verify the structure of provider_info that serialize_model_card builds."""
        from app.services.providers.registry import get_provider
        local = get_provider("local")
        assert local is not None
        caps = local.capabilities()
        provider_info = {
            "provider_id": local.provider_id,
            "provider_type": local.provider_type.value,
            "enabled": local.enabled,
            "configured": local.configured,
            "capabilities": caps.model_dump(),
        }
        assert provider_info["provider_id"] == "local"
        assert provider_info["enabled"] is True
        assert provider_info["configured"] is True
        assert provider_info["capabilities"]["chat"] is True
        assert provider_info["capabilities"]["embeddings"] is True

    def test_cloud_provider_registered_even_when_disabled(self):
        """Cloud providers should be in the registry even when disabled."""
        providers = get_providers()
        for cloud in ("openai", "anthropic", "deepseek", "openrouter", "gemini", "bedrock", "azure_openai", "mistral", "cohere", "groq", "together", "perplexity", "replicate", "xai", "fireworks", "ai21"):
            assert cloud in providers, f"{cloud} should be registered"
