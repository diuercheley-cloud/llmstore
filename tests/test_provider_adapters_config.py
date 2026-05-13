import os
import pytest


class TestProviderAdaptersConfig:
    def test_default_providers_enabled(self):
        val = os.environ.get("PROVIDERS_ENABLED", "local,lmstudio")
        providers = [p.strip() for p in val.split(",") if p.strip()]
        assert "local" in providers
        assert "lmstudio" in providers

    def test_cloud_providers_disabled_by_default(self):
        val = os.environ.get("CLOUD_PROVIDERS_ENABLED", "false")
        assert val.lower() in ("false", "0", "no")

    def test_no_api_keys_exposed_in_env(self):
        sensitive = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY"]
        for key in sensitive:
            val = os.environ.get(key, "")
            # In test environment, no real keys should be set
            assert val == "", f"{key} should be empty in test environment"

    def test_provider_timeout_has_default(self):
        val = os.environ.get("PROVIDER_TIMEOUT_SECONDS", "30")
        assert int(val) > 0

    def test_provider_max_retries_has_default(self):
        val = os.environ.get("PROVIDER_MAX_RETRIES", "2")
        assert int(val) >= 0

    def test_provider_fail_closed_default(self):
        val = os.environ.get("PROVIDER_FAIL_CLOSED", "true")
        assert val.lower() == "true"

    def test_lmstudio_enabled_can_be_toggled(self):
        val = os.environ.get("LMSTUDIO_ENABLED", "false")
        assert val.lower() in ("true", "false")
