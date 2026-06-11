import os
from pathlib import Path
from typing import Any, Dict, List, Self

import yaml
from pydantic import computed_field, model_validator
from pydantic_settings import SettingsConfigDict

from control_plane.app.core.config_agent import AgentSettings
from control_plane.app.core.config_commercial import CommercialSettings
from control_plane.app.core.cors import resolve_cors_origins
from control_plane.app.services.config.core_config import CoreConfig
from control_plane.app.services.config.security_config import SecurityConfig
from control_plane.app.services.config.backup_config import BackupConfig
from control_plane.app.services.config.plugins_config import PluginsConfig
from control_plane.app.services.config.billing_config import BillingConfig
from control_plane.app.services.config.agents_config import AgentsConfig


def _read_dotenv_keys() -> set[str]:
    keys: set[str] = set()
    for p in (Path(".env"),):
        try:
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            keys.add(line.split("=", 1)[0].strip())
        except Exception:
            pass
    return keys


def _read_dotenv_value(key: str) -> str | None:
    value = None
    for path in (Path(".env"), Path(".env.local")):
        try:
            if not path.exists():
                continue
            with open(path, encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    candidate_key, candidate_value = line.split("=", 1)
                    if candidate_key.strip() == key:
                        value = candidate_value.strip().strip("\"'")
        except OSError:
            continue
    return value


class BaseAppConfig(
    AgentSettings,
    CommercialSettings,
    CoreConfig,
    SecurityConfig,
    BackupConfig,
    PluginsConfig,
    BillingConfig,
    AgentsConfig,
):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    @model_validator(mode='after')
    def validate_sensitive_fields(self) -> Self:
        sensitive_fields = [
            "jwt_secret", "admin_token", "pinecone_api_key", "sendgrid_api_key",
            "fcm_api_key", "stripe_secret_key", "stripe_webhook_secret",
            "openai_api_key", "anthropic_api_key", "deepseek_api_key",
            "openrouter_api_key", "gemini_api_key", "aws_secret_access_key",
            "azure_openai_api_key", "mistral_api_key", "cohere_api_key",
            "groq_api_key", "together_api_key", "perplexity_api_key",
            "replicate_api_key", "xai_api_key", "fireworks_api_key",
            "ai21_api_key", "oauth_google_client_secret", "oauth_github_client_secret",
            "enterprise_sso_azure_client_secret", "enterprise_sso_okta_client_secret",
            "vault_token", "a2a_api_key"
        ]

        for field in sensitive_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if isinstance(value, str) and value:
                    if value == "change-me-at-all-costs" or value == "default-admin-token":
                        raise ValueError(f"{field.upper()} must be set to a secure, unique value.")
                    if len(value) < 32:
                        raise ValueError(f"{field.upper()} is too short. Minimum 32 characters required.")
        return self

    @computed_field
    @property
    def max_completion_tokens(self) -> int:
        return self.inference_max_completion_tokens

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        return resolve_cors_origins(
            self.cors_allow_origins,
            self.app_public_url,
            self.localhost_mode,
            self.local_appliance_mode
        )


def load_config_profile(profile: str = "lite") -> Dict[str, Any]:
    config_dir = Path(__file__).resolve().parents[3] / "config" / "profiles"
    profile_path = config_dir / f"{profile}.yaml"

    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    raise ValueError(f"Unknown operational profile: {profile}")


def _profile_settings(profile_config: Dict[str, Any]) -> Dict[str, Any]:
    settings = profile_config.get("settings", profile_config)
    if not isinstance(settings, dict):
        raise ValueError("Operational profile settings must be a mapping")

    environment_keys = set(os.environ) | _read_dotenv_keys()
    return {
        key: value
        for key, value in settings.items()
        if key not in environment_keys
    }


class ConfigService:
    _instance = None

    def __init__(self):
        self.profile = (
            os.environ.get("OPERATIONAL_PROFILE")
            or _read_dotenv_value("OPERATIONAL_PROFILE")
            or os.environ.get("DEPLOYMENT_PROFILE")
            or _read_dotenv_value("DEPLOYMENT_PROFILE")
            or "lite"
        )
        self.profile_config = load_config_profile(self.profile)
        settings = _profile_settings(self.profile_config)
        settings.setdefault("OPERATIONAL_PROFILE", self.profile)
        self.settings = BaseAppConfig(**settings)

    def get_profile_summary(self) -> Dict[str, Any]:
        features = self.profile_config.get("features", {})
        if not isinstance(features, dict):
            raise ValueError("Operational profile features must be a mapping")

        normalized_features = {
            str(name): bool(enabled)
            for name, enabled in features.items()
        }
        return {
            "profile": self.profile,
            "description": self.profile_config.get("description", ""),
            "features": normalized_features,
            "active_features": sorted(
                name for name, enabled in normalized_features.items() if enabled
            ),
            "disabled_features": sorted(
                name for name, enabled in normalized_features.items() if not enabled
            ),
        }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        global _service
        cls._instance = None
        _service = None

    @property
    def config(self):
        return self.settings


_service = None


def get_config_service():
    global _service
    if _service is None:
        _service = ConfigService.get_instance()
    return _service
