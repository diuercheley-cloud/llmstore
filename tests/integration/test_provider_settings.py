import os

import pytest
from app.core.config import get_settings
from app.services.provider_settings import apply_runtime_updates
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_provider_settings_page_access(admin_client: AsyncClient):
    response = await admin_client.get("/provider-settings")
    assert response.status_code == 200
    assert "Atualize o registry de providers" in response.text
    assert "Salvar em `.env.local`" in response.text


@pytest.mark.asyncio
async def test_provider_settings_page_disabled_in_public_exposure(admin_client: AsyncClient):
    settings = get_settings()
    previous = settings.public_exposure
    settings.public_exposure = True
    try:
        response = await admin_client.get("/provider-settings")
        assert response.status_code == 404
        assert response.json()["detail"] == "provider settings disabled in public exposure mode"

        static_response = await admin_client.get("/static/provider-settings/index.html")
        assert static_response.status_code == 404
        assert static_response.json()["detail"] == "provider settings disabled in public exposure mode"
    finally:
        settings.public_exposure = previous


@pytest.mark.asyncio
async def test_provider_settings_round_trip(admin_client: AsyncClient, admin_token_headers: dict[str, str], tmp_path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join([
            "CLOUD_PROVIDERS_ENABLED=false",
            "REAL_PROVIDER_VALIDATION_ENABLED=false",
            "REAL_PROVIDER_MAX_COST_BRL=2.00",
            "REAL_PROVIDER_TIMEOUT_SECONDS=30",
            "OPENAI_PROVIDER_ENABLED=false",
            "OPENAI_API_KEY=",
            "OPENAI_BASE_URL=https://api.openai.com/v1",
            "OPENAI_CHAT_MODEL=",
            "OPENAI_EMBEDDINGS_MODEL=",
            "DEEPSEEK_PROVIDER_ENABLED=false",
            "DEEPSEEK_API_KEY=",
            "DEEPSEEK_BASE_URL=https://api.deepseek.com",
            "DEEPSEEK_CHAT_MODEL=",
            "ANTHROPIC_PROVIDER_ENABLED=false",
            "ANTHROPIC_API_KEY=",
            "ANTHROPIC_BASE_URL=https://api.anthropic.com",
            "ANTHROPIC_MODEL=",
            "OPENROUTER_API_KEY=",
            "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1",
            "",
        ]),
        encoding="utf-8",
    )
    monkeypatch.setenv("PROVIDER_SETTINGS_ENV_FILE", str(env_file))
    monkeypatch.setenv("CLOUD_PROVIDERS_ENABLED", "false")
    monkeypatch.setenv("REAL_PROVIDER_VALIDATION_ENABLED", "false")
    monkeypatch.setenv("REAL_PROVIDER_MAX_COST_BRL", "2.00")
    monkeypatch.setenv("REAL_PROVIDER_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("OPENAI_PROVIDER_ENABLED", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "")
    monkeypatch.setenv("OPENAI_EMBEDDINGS_MODEL", "")
    monkeypatch.setenv("DEEPSEEK_PROVIDER_ENABLED", "false")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_CHAT_MODEL", "")
    monkeypatch.setenv("ANTHROPIC_PROVIDER_ENABLED", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    monkeypatch.setenv("ANTHROPIC_MODEL", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    apply_runtime_updates({
        "CLOUD_PROVIDERS_ENABLED": "false",
        "REAL_PROVIDER_VALIDATION_ENABLED": "false",
        "REAL_PROVIDER_MAX_COST_BRL": "2.00",
        "REAL_PROVIDER_TIMEOUT_SECONDS": "30",
        "OPENAI_PROVIDER_ENABLED": "false",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "OPENAI_CHAT_MODEL": "",
        "OPENAI_EMBEDDINGS_MODEL": "",
        "DEEPSEEK_PROVIDER_ENABLED": "false",
        "DEEPSEEK_API_KEY": "",
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_CHAT_MODEL": "",
        "ANTHROPIC_PROVIDER_ENABLED": "false",
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        "ANTHROPIC_MODEL": "",
        "OPENROUTER_API_KEY": "",
        "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    })

    initial = await admin_client.get("/admin/providers/configuration", headers=admin_token_headers)
    assert initial.status_code == 200
    assert initial.json()["providers"]["openai"]["configured"] is False

    payload = {
        "global": {
            "cloud_providers_enabled": True,
            "real_provider_validation_enabled": False,
            "real_provider_max_cost_brl": 4.25,
            "real_provider_timeout_seconds": 45,
        },
        "providers": {
            "openai": {
                "enabled": True,
                "api_key": "TEST_OPENAI_API_KEY",
                "clear_api_key": False,
                "base_url": "https://api.openai.com/v1",
                "chat_model": "gpt-4o-mini",
                "embeddings_model": "text-embedding-3-small",
            },
            "deepseek": {
                "enabled": True,
                "api_key": "TEST_DEEPSEEK_API_KEY",
                "clear_api_key": False,
                "base_url": "https://api.deepseek.com",
                "chat_model": "deepseek-chat",
            },
            "anthropic": {
                "enabled": True,
                "api_key": "TEST_ANTHROPIC_API_KEY",
                "clear_api_key": False,
                "base_url": "https://api.anthropic.com",
                "model": "claude-3-haiku-20240307",
            },
            "openrouter": {
                "api_key": "TEST_OPENROUTER_API_KEY",
                "clear_api_key": False,
                "base_url": "https://openrouter.ai/api/v1",
            },
        },
    }

    response = await admin_client.put("/admin/providers/configuration", headers=admin_token_headers, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "provider configuration updated"
    assert body["configuration"]["global"]["cloud_providers_enabled"] is True
    assert body["configuration"]["providers"]["openai"]["masked_api_key"].startswith("TEST")
    assert body["configuration"]["providers"]["deepseek"]["configured"] is True
    assert body["configuration"]["providers"]["anthropic"]["configured"] is True

    updated_env = env_file.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=TEST_OPENAI_API_KEY" in updated_env
    assert "DEEPSEEK_CHAT_MODEL=deepseek-chat" in updated_env
    assert "OPENROUTER_API_KEY=TEST_OPENROUTER_API_KEY" in updated_env
    assert os.environ["CLOUD_PROVIDERS_ENABLED"] == "true"
    assert os.environ["REAL_PROVIDER_TIMEOUT_SECONDS"] == "45"

    cleared = await admin_client.put(
        "/admin/providers/configuration",
        headers=admin_token_headers,
        json={
            "global": {
                "cloud_providers_enabled": True,
                "real_provider_validation_enabled": False,
                "real_provider_max_cost_brl": 4.25,
                "real_provider_timeout_seconds": 45,
            },
            "providers": {
                "openai": {
                    "enabled": True,
                    "clear_api_key": True,
                    "base_url": "https://api.openai.com/v1",
                    "chat_model": "gpt-4o-mini",
                    "embeddings_model": "text-embedding-3-small",
                },
                "deepseek": {
                    "enabled": True,
                    "base_url": "https://api.deepseek.com",
                    "chat_model": "deepseek-chat",
                },
                "anthropic": {
                    "enabled": True,
                    "base_url": "https://api.anthropic.com",
                    "model": "claude-3-haiku-20240307",
                },
                "openrouter": {
                    "base_url": "https://openrouter.ai/api/v1",
                },
            },
        },
    )
    assert cleared.status_code == 200
    assert "OPENAI_API_KEY=\n" in env_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_provider_settings_ignores_dummy_placeholder_keys(
    admin_client: AsyncClient,
    admin_token_headers: dict[str, str],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join([
            "CLOUD_PROVIDERS_ENABLED=true",
            "REAL_PROVIDER_VALIDATION_ENABLED=false",
            "OPENAI_PROVIDER_ENABLED=true",
            "OPENAI_API_KEY=placeholder-use-real-key",
            "DEEPSEEK_PROVIDER_ENABLED=true",
            "DEEPSEEK_API_KEY=replace-with-real-key",
            "ANTHROPIC_PROVIDER_ENABLED=true",
            "ANTHROPIC_API_KEY=changeme",
            "OPENROUTER_API_KEY=sk-example-openrouter-key",
            "OPENROUTER_BASE_URL=https://openrouter.ai/api/v1",
            "",
        ]),
        encoding="utf-8",
    )
    monkeypatch.setenv("PROVIDER_SETTINGS_ENV_FILE", str(env_file))
    apply_runtime_updates({
        "CLOUD_PROVIDERS_ENABLED": "true",
        "REAL_PROVIDER_VALIDATION_ENABLED": "false",
        "OPENAI_PROVIDER_ENABLED": "true",
        "OPENAI_API_KEY": "placeholder-use-real-key",
        "DEEPSEEK_PROVIDER_ENABLED": "true",
        "DEEPSEEK_API_KEY": "replace-with-real-key",
        "ANTHROPIC_PROVIDER_ENABLED": "true",
        "ANTHROPIC_API_KEY": "changeme",
        "OPENROUTER_API_KEY": "sk-example-openrouter-key",
        "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    })

    response = await admin_client.get("/admin/providers/configuration", headers=admin_token_headers)
    assert response.status_code == 200
    providers = response.json()["providers"]
    assert providers["openai"]["configured"] is False
    assert providers["openai"]["masked_api_key"] is None
    assert providers["deepseek"]["configured"] is False
    assert providers["deepseek"]["masked_api_key"] is None
    assert providers["anthropic"]["configured"] is False
    assert providers["anthropic"]["masked_api_key"] is None
    assert providers["openrouter"]["configured"] is True
    assert providers["openrouter"]["masked_api_key"].startswith("sk-e")
