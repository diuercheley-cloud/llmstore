import os

import pytest

from control_plane.app.services.config_service import BaseAppConfig, ConfigService


def test_precedence_env_over_yaml(monkeypatch):
    ConfigService.reset_instance()
    # Set a specific profile
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "local")

    # Set an env var that is also in the local profile
    monkeypatch.setenv("DEBUG", "true")

    config = ConfigService.get_instance().config
    assert config.debug is True


def test_sensitive_fields_validation(monkeypatch):
    ConfigService.reset_instance()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("JWT_SECRET", "short")

    with pytest.raises(ValueError, match="too short"):
        ConfigService.get_instance()


def test_config_precedence():
    """Verify that environment variables take precedence over profile defaults."""
    os.environ["PROJECT_NAME"] = "env-project-name"
    config = BaseAppConfig(
        database_url="sqlite:///:memory:",
        jwt_secret="a-long-enough-and-very-secure-secret-key-32-chars-plus",
    )
    assert config.project_name == "env-project-name"
    del os.environ["PROJECT_NAME"]
