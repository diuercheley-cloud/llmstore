from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from control_plane.app.services.config_service import ConfigService

PROFILES = ("lite", "standard", "agentic", "enterprise")
PROFILE_DIR = Path(__file__).resolve().parents[3] / "config" / "profiles"


@pytest.fixture(autouse=True)
def reset_config_service():
    ConfigService.reset_instance()
    yield
    ConfigService.reset_instance()


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_starts_with_valid_config(profile, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPERATIONAL_PROFILE", profile)
    monkeypatch.delenv("DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    service = ConfigService.get_instance()

    assert service.profile == profile
    assert service.config.operational_profile == profile
    assert service.get_profile_summary()["profile"] == profile

    if profile == "lite":
        assert service.config.database_url.startswith("sqlite+aiosqlite:")
        assert service.config.create_tables_on_startup is True
    else:
        assert service.config.database_url.startswith("postgresql+asyncpg:")

    if profile in {"agentic", "enterprise"}:
        assert service.config.agent_memory_enabled is True
        assert service.config.agent_tool_registry_enabled is True
        assert service.config.agent_stateful_workflows_enabled is True
        assert service.config.agent_runtime_enabled is True


def test_profiles_are_progressive():
    manifests = {
        profile: yaml.safe_load((PROFILE_DIR / f"{profile}.yaml").read_text(encoding="utf-8"))
        for profile in PROFILES
    }

    lite = manifests["lite"]["features"]
    standard = manifests["standard"]["features"]
    agentic = manifests["agentic"]["features"]
    enterprise = manifests["enterprise"]["features"]

    assert lite["sqlite"] is True
    assert lite["loki"] is False
    assert lite["tempo"] is False
    assert lite["prometheus"] is False
    assert lite["multi_tenant"] is False
    assert lite["federation"] is False
    assert lite["marketplace"] is False
    assert lite["rag_basic"] is True
    assert lite["inference_proxy"] is True

    assert standard["postgresql"] is True
    assert standard["observability_basic"] is True
    assert standard["multi_model"] is True

    assert agentic["memory"] is True
    assert agentic["tools"] is True
    assert agentic["workflows"] is True
    assert agentic["agents"] is True

    assert enterprise["sqlite"] is False
    assert all(enabled for feature, enabled in enterprise.items() if feature != "sqlite")


def test_environment_overrides_profile_settings(monkeypatch):
    monkeypatch.setenv("OPERATIONAL_PROFILE", "lite")
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    config = ConfigService.get_instance().config

    assert config.observability_enabled is True
    assert config.database_url == "sqlite+aiosqlite:///:memory:"


def test_profile_is_loaded_from_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPERATIONAL_PROFILE", raising=False)
    monkeypatch.delenv("DEPLOYMENT_PROFILE", raising=False)
    (tmp_path / ".env").write_text("OPERATIONAL_PROFILE=standard\n", encoding="utf-8")

    assert ConfigService.get_instance().profile == "standard"


def test_lite_is_the_default_profile(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPERATIONAL_PROFILE", raising=False)
    monkeypatch.delenv("DEPLOYMENT_PROFILE", raising=False)

    assert ConfigService.get_instance().profile == "lite"


def test_system_profile_endpoint(monkeypatch):
    monkeypatch.setenv("OPERATIONAL_PROFILE", "agentic")
    ConfigService.reset_instance()

    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/system/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"] == "agentic"
    assert "agents" in payload["active_features"]
    assert "marketplace" in payload["disabled_features"]
