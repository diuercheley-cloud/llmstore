import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Self

import yaml
from pydantic import computed_field, model_validator
from pydantic_settings import SettingsConfigDict

from control_plane.app.core.config_agent import AgentSettings
from control_plane.app.core.config_commercial import CommercialSettings
from control_plane.app.core.cors import get_cors_warnings, resolve_cors_origins
from control_plane.app.services.config.core_config import CoreConfig
from control_plane.app.services.config.security_config import SecurityConfig
from control_plane.app.services.config.backup_config import BackupConfig
from control_plane.app.services.config.plugins_config import PluginsConfig
from control_plane.app.services.config.billing_config import BillingConfig
from control_plane.app.services.config.agents_config import AgentsConfig

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ConfigDetail:
    value: Any
    source: str


def _read_dotenv_keys() -> set[str]:
    keys: set[str] = set()
    paths = (
        Path(".env"),
        Path(".env.local"),
        Path("env/observability.env"),
        Path("env/commercial.env"),
        Path("env/agentic.env"),
        Path("env/enterprise.env"),
    )
    for p in paths:
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
    paths = (
        Path(".env"),
        Path(".env.local"),
        Path("env/observability.env"),
        Path("env/commercial.env"),
        Path("env/agentic.env"),
        Path("env/enterprise.env"),
    )
    for path in paths:
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
        env_file=(
            ".env",
            "env/observability.env",
            "env/commercial.env",
            "env/agentic.env",
            "env/enterprise.env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    @model_validator(mode='before')
    @classmethod
    def apply_simplification_profiles(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps high-level profiles to individual feature flags.
        """
        if not isinstance(data, dict):
            return data

        def _get_val(key: str) -> Any:
            return data.get(key) or data.get(key.lower()) or os.environ.get(key) or os.environ.get(key.lower())

        def _set_with_warning(key: str, value: Any, profile_name: str, profile_value: str):
            if key in data and data[key] != value:
                # Individual flag is set and differs from profile default
                # We keep the individual flag (compatibility) but warn
                logger.warning(
                    f"DEPRECATION: Feature flag '{key}' is explicitly set to '{data[key]}'. "
                    f"This flag is now managed by '{profile_name}={profile_value}'. "
                    f"Individual flag overrides will be removed in v3.0."
                )
            else:
                data[key] = value

        # 1. Map AGENT_TOOL_SET
        tool_set = _get_val("AGENT_TOOL_SET") or "standard"
        if tool_set == "minimal":
            _set_with_warning("AGENT_HTTP_TOOL_ENABLED", False, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_DB_READ_TOOL_ENABLED", False, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_SHELL_TOOL_ENABLED", False, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_TOOL_ADAPTERS_ENABLED", False, "AGENT_TOOL_SET", tool_set)
        elif tool_set == "standard":
            _set_with_warning("AGENT_HTTP_TOOL_ENABLED", True, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_DB_READ_TOOL_ENABLED", True, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_SHELL_TOOL_ENABLED", False, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_TOOL_ADAPTERS_ENABLED", True, "AGENT_TOOL_SET", tool_set)
        elif tool_set == "full":
            _set_with_warning("AGENT_HTTP_TOOL_ENABLED", True, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_DB_READ_TOOL_ENABLED", True, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_SHELL_TOOL_ENABLED", True, "AGENT_TOOL_SET", tool_set)
            _set_with_warning("AGENT_TOOL_ADAPTERS_ENABLED", True, "AGENT_TOOL_SET", tool_set)

        # 2. Map OBSERVABILITY_PROFILE
        obs_profile = _get_val("OBSERVABILITY_PROFILE") or "basic"
        if obs_profile == "off":
            _set_with_warning("OBSERVABILITY_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("AGENT_OBSERVABILITY_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("PROMETHEUS_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("LOKI_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("TEMPO_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
        elif obs_profile == "basic":
            _set_with_warning("OBSERVABILITY_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("AGENT_OBSERVABILITY_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("PROMETHEUS_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("LOKI_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("TEMPO_ENABLED", False, "OBSERVABILITY_PROFILE", obs_profile)
        elif obs_profile == "full":
            _set_with_warning("OBSERVABILITY_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("AGENT_OBSERVABILITY_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("PROMETHEUS_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("LOKI_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)
            _set_with_warning("TEMPO_ENABLED", True, "OBSERVABILITY_PROFILE", obs_profile)

        # 3. Map COMMERCIAL_PROFILE
        comm_profile = _get_val("COMMERCIAL_PROFILE") or "off"
        if comm_profile == "off":
            _set_with_warning("CLOUD_PROVIDERS_ENABLED", False, "COMMERCIAL_PROFILE", comm_profile)
            _set_with_warning("COMMERCIAL_GUARDRAILS_ENABLED", False, "COMMERCIAL_PROFILE", comm_profile)
            _set_with_warning("PAYMENT_PROCESSING_ENABLED", False, "COMMERCIAL_PROFILE", comm_profile)
        elif comm_profile == "billing":
            _set_with_warning("CLOUD_PROVIDERS_ENABLED", True, "COMMERCIAL_PROFILE", comm_profile)
            _set_with_warning("COMMERCIAL_GUARDRAILS_ENABLED", True, "COMMERCIAL_PROFILE", comm_profile)
            _set_with_warning("PAYMENT_PROCESSING_ENABLED", False, "COMMERCIAL_PROFILE", comm_profile)
        elif comm_profile == "billing_payments":
            _set_with_warning("CLOUD_PROVIDERS_ENABLED", True, "COMMERCIAL_PROFILE", comm_profile)
            _set_with_warning("COMMERCIAL_GUARDRAILS_ENABLED", True, "COMMERCIAL_PROFILE", comm_profile)
            _set_with_warning("PAYMENT_PROCESSING_ENABLED", True, "COMMERCIAL_PROFILE", comm_profile)

        # 4. Map SECURITY_PROFILE
        sec_profile = _get_val("SECURITY_PROFILE") or "local"
        if sec_profile == "local":
            _set_with_warning("RBAC_ADMIN_ENABLED", False, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("ENTERPRISE_SSO_ENABLED", False, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("PKI_ENABLED", False, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("HARDWARE_TRUST_ENABLED", False, "SECURITY_PROFILE", sec_profile)
        elif sec_profile == "standard":
            _set_with_warning("RBAC_ADMIN_ENABLED", True, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("ENTERPRISE_SSO_ENABLED", False, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("PKI_ENABLED", False, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("HARDWARE_TRUST_ENABLED", False, "SECURITY_PROFILE", sec_profile)
        elif sec_profile == "enterprise":
            _set_with_warning("RBAC_ADMIN_ENABLED", True, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("ENTERPRISE_SSO_ENABLED", True, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("PKI_ENABLED", True, "SECURITY_PROFILE", sec_profile)
            _set_with_warning("HARDWARE_TRUST_ENABLED", True, "SECURITY_PROFILE", sec_profile)

        # 5. Invalid Combinations Validation
        if comm_profile != "off" and sec_profile == "local":
            raise ValueError(f"Incompatible Profiles: COMMERCIAL_PROFILE='{comm_profile}' requires SECURITY_PROFILE='standard' or 'enterprise' (current: '{sec_profile}').")
        
        if tool_set == "full" and sec_profile == "local":
            raise ValueError(f"Incompatible Profiles: AGENT_TOOL_SET='full' (includes Shell access) requires SECURITY_PROFILE='standard' or 'enterprise' (current: '{sec_profile}').")

        local_appliance_mode = data.get("LOCAL_APPLIANCE_MODE", data.get("local_appliance_mode", False))
        if local_appliance_mode:
            data["LOCALHOST_MODE"] = True
            data["PUBLIC_EXPOSURE"] = False
            data["PUBLIC_SIGNUP_ENABLED"] = False
            data["LOCAL_BILLING_MODE"] = "manual"

        return data

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

        is_production = getattr(self, "app_env", "local") in ["production", "enterprise-production", "local-production"]
        insecure_defaults = [
            "change-me-at-all-costs", 
            "default-admin-token", 
            "ChangeMe_ProdAdminToken_2026!", 
            "QuickstartAdminToken-ChangeMe-1234",
            "quickstart-jwt-secret-change-me"
        ]

        for field in sensitive_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if isinstance(value, str) and value:
                    if value in insecure_defaults:
                        if is_production:
                            raise RuntimeError(f"SECURITY BREACH: {field.upper()} is using an insecure default value in a production environment ({self.app_env}).")
                        else:
                            raise ValueError(f"{field.upper()}: Default value is insecure; set a secure, unique value.")
                    if field == "jwt_secret" and len(value) < 32:
                        raise ValueError("JWT_SECRET is too short. Minimum 32 characters required.")
                    if is_production and len(value) < 32:
                        raise RuntimeError(f"SECURITY BREACH: {field.upper()} is too short for production. Minimum 32 characters required.")
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

    @computed_field
    @property
    def cors_warnings(self) -> List[dict[str, str]]:
        return get_cors_warnings(
            self.cors_allow_origins,
            self.local_appliance_mode
        )


def load_config_profile(profile: str = "lite") -> Dict[str, Any]:
    candidates = [
        Path(__file__).resolve().parents[3] / "config" / "profiles",
        Path("/config/profiles"),
    ]
    for config_dir in candidates:
        profile_path = config_dir / f"{profile}.yaml"
        if profile_path.exists():
            with open(profile_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    raise ValueError(f"Unknown operational profile: {profile}")


def _resolve_file_secret(value: str) -> str:
    """Read secret from file if the path exists."""
    if os.path.isfile(value):
        try:
            with open(value, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return value


def _profile_settings(profile_config: Dict[str, Any]) -> Dict[str, Any]:
    settings = profile_config.get("settings", profile_config)
    if not isinstance(settings, dict):
        raise ValueError("Operational profile settings must be a mapping")

    # environment_keys includes both real env vars and keys from .env files
    # We need to check for _FILE counterparts and resolve them
    env_keys = set(os.environ) | _read_dotenv_keys()
    
    # Pre-resolve secrets for Pydantic
    for key in list(env_keys):
        if key.endswith("_FILE"):
            base_key = key[:-5]
            # If ADMIN_TOKEN_FILE exists but ADMIN_TOKEN doesn't in os.environ, 
            # we should put the resolved value into os.environ so Pydantic sees it via AliasChoices.
            # However, pydantic-settings handles env vars directly. 
            # If we have ADMIN_TOKEN_FILE in os.environ, Pydantic's AliasChoices will pick it up
            # but it will be the PATH, not the CONTENT.
            # So we MUST resolve it and put it in os.environ or pass it to BaseAppConfig.
            
            file_path = os.environ.get(key) or _read_dotenv_value(key)
            if file_path:
                secret_value = _resolve_file_secret(file_path)
                # Inject the resolved secret into environment so Pydantic sees it
                if base_key not in os.environ:
                    os.environ[base_key] = secret_value

    return {
        key: value
        for key, value in settings.items()
        if key not in env_keys
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
        self._runtime_overrides: Dict[str, Any] = {}
        self._feature_flags = self.profile_config.get("features", {})
        self._file_configs: Dict[str, Dict[str, Any]] = {}
        settings = _profile_settings(self.profile_config)
        settings.setdefault("OPERATIONAL_PROFILE", self.profile)
        self.settings = BaseAppConfig(**settings)

    def clear_runtime_overrides(self) -> None:
        self._runtime_overrides.clear()

    def set_runtime_override(self, key: str, value: Any) -> None:
        self._runtime_overrides[key.upper()] = value

    def _file_value(self, key: str) -> tuple[Any, str] | None:
        normalized = key.lower()

        def visit(mapping: Dict[str, Any], prefix: str = "") -> Any:
            for name, value in mapping.items():
                path = f"{prefix}_{name}".strip("_").lower()
                if path == normalized:
                    return value
                if isinstance(value, dict):
                    found = visit(value, path)
                    if found is not None:
                        return found
            return None

        for filename, config in self._file_configs.items():
            value = visit(config)
            if value is not None:
                return value, f"file:{filename}"
        return None

    def get_detailed(self, key: str) -> ConfigDetail:
        normalized = key.upper()
        if normalized in self._runtime_overrides:
            return ConfigDetail(self._runtime_overrides[normalized], "runtime")
        if normalized in os.environ:
            field_name = next(
                (name for name, field in type(self.settings).model_fields.items()
                 if (field.alias or name.upper()) == normalized),
                None,
            )
            if field_name:
                value = type(getattr(self.settings, field_name))(os.environ[normalized])
                if isinstance(getattr(self.settings, field_name), bool):
                    value = os.environ[normalized].lower() in {"1", "true", "yes", "on"}
                return ConfigDetail(value, "env")
            return ConfigDetail(os.environ[normalized], "env")
        if normalized in self._feature_flags:
            return ConfigDetail(self._feature_flags[normalized], "file:feature-flags.yaml")
        file_value = self._file_value(normalized)
        if file_value:
            return ConfigDetail(*file_value)
        field_name = next(
            (name for name, field in type(self.settings).model_fields.items()
             if (field.alias or name.upper()) == normalized),
            None,
        )
        if field_name:
            return ConfigDetail(getattr(self.settings, field_name), "default")
        return ConfigDetail(None, "default")

    def get_effective_config(self, *, redact: bool = True) -> List[Dict[str, Any]]:
        keys = {
            (field.alias or name.upper())
            for name, field in type(self.settings).model_fields.items()
        } | set(self._runtime_overrides) | set(self._feature_flags)
        result = []
        for key in sorted(keys):
            detail = self.get_detailed(key)
            value = detail.value
            if redact and any(marker in key for marker in ("PASSWORD", "SECRET", "TOKEN", "API_KEY")) and value:
                value = "********"
            result.append({"key": key, "value": value, "source": detail.source})
        return result

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
