from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.services.admin_model_management import project_root
from app.services.providers.registry import reload_registry

_ENV_LINE_RE = re.compile(r"^([A-Z0-9_]+)=(.*)$")
_TEST_API_KEY_MARKERS = (
    "dummy-test-key-not-valid",
    "not-valid",
    "test_api_key",
    "placeholder",
    "replace-with",
    "change-me",
    "changeme",
)

_MANAGED_KEYS = [
    "CLOUD_PROVIDERS_ENABLED",
    "REAL_PROVIDER_VALIDATION_ENABLED",
    "REAL_PROVIDER_MAX_COST_BRL",
    "REAL_PROVIDER_TIMEOUT_SECONDS",
    "OPENAI_PROVIDER_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_CHAT_MODEL",
    "OPENAI_EMBEDDINGS_MODEL",
    "DEEPSEEK_PROVIDER_ENABLED",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_CHAT_MODEL",
    "ANTHROPIC_PROVIDER_ENABLED",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "OPENROUTER_PROVIDER_ENABLED",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
]


def env_file_path() -> Path:
    configured = os.environ.get("PROVIDER_SETTINGS_ENV_FILE", "").strip()
    if configured:
        return Path(configured)
    return project_root() / ".env.local"


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def is_real_api_key_configured(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    normalized = value.strip().lower()
    return not any(marker in normalized for marker in _TEST_API_KEY_MARKERS)


def masked_real_api_key(value: str | None) -> str | None:
    if not is_real_api_key_configured(value):
        return None
    return _mask(value)


def _bool_string(value: bool) -> str:
    return "true" if value else "false"


def _read_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _read_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in _read_env_lines(path):
        match = _ENV_LINE_RE.match(line)
        if not match:
            continue
        values[match.group(1)] = match.group(2)
    return values


def _coerce_bool(value: str | None, fallback: bool) -> bool:
    if value is None:
        return fallback
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _coerce_float(value: str | None, fallback: float) -> float:
    if value is None or not value.strip():
        return fallback
    try:
        return float(value.strip())
    except ValueError:
        return fallback


def _coerce_int(value: str | None, fallback: int) -> int:
    if value is None or not value.strip():
        return fallback
    try:
        return int(value.strip())
    except ValueError:
        return fallback


def write_env_updates(updates: dict[str, str]) -> Path:
    path = env_file_path()
    lines = _read_env_lines(path)
    remaining = dict(updates)
    written = False
    new_lines: list[str] = []

    for line in lines:
        match = _ENV_LINE_RE.match(line)
        if not match:
            new_lines.append(line)
            continue
        key = match.group(1)
        if key not in remaining:
            new_lines.append(line)
            continue
        new_lines.append(f"{key}={remaining.pop(key)}")
        written = True

    if remaining:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        if not written:
            new_lines.append("# Provider Settings")
        for key in _MANAGED_KEYS:
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}")
        for key, value in remaining.items():
            new_lines.append(f"{key}={value}")

    content = "\n".join(new_lines).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def apply_runtime_updates(updates: dict[str, str]) -> None:
    for key, value in updates.items():
        os.environ[key] = value
    current = get_settings()
    refreshed = Settings()
    for field_name in Settings.model_fields:
        setattr(current, field_name, getattr(refreshed, field_name))
    reload_registry()


def build_provider_configuration() -> dict[str, Any]:
    settings = get_settings()
    env_path = env_file_path()
    env_values = _read_env_values(env_path)

    cloud_enabled = _coerce_bool(
        env_values.get("CLOUD_PROVIDERS_ENABLED"),
        settings.cloud_providers_enabled,
    )
    validation_enabled = _coerce_bool(
        env_values.get("REAL_PROVIDER_VALIDATION_ENABLED"),
        settings.real_provider_validation_enabled,
    )
    max_cost_brl = _coerce_float(
        env_values.get("REAL_PROVIDER_MAX_COST_BRL"),
        settings.real_provider_max_cost_brl,
    )
    timeout_seconds = _coerce_int(
        env_values.get("REAL_PROVIDER_TIMEOUT_SECONDS"),
        settings.provider_timeout_seconds,
    )

    openai_enabled = _coerce_bool(
        env_values.get("OPENAI_PROVIDER_ENABLED"),
        settings.openai_provider_enabled,
    )
    openai_api_key = env_values.get("OPENAI_API_KEY", settings.openai_api_key)
    openai_base_url = env_values.get("OPENAI_BASE_URL", settings.openai_base_url)
    openai_chat_model = env_values.get("OPENAI_CHAT_MODEL", settings.openai_chat_model)
    openai_embeddings_model = env_values.get(
        "OPENAI_EMBEDDINGS_MODEL",
        settings.openai_embeddings_model,
    )

    deepseek_enabled = _coerce_bool(
        env_values.get("DEEPSEEK_PROVIDER_ENABLED"),
        settings.deepseek_provider_enabled,
    )
    deepseek_api_key = env_values.get("DEEPSEEK_API_KEY", settings.deepseek_api_key)
    deepseek_base_url = env_values.get("DEEPSEEK_BASE_URL", settings.deepseek_base_url)
    deepseek_chat_model = env_values.get("DEEPSEEK_CHAT_MODEL", settings.deepseek_chat_model)

    anthropic_enabled = _coerce_bool(
        env_values.get("ANTHROPIC_PROVIDER_ENABLED"),
        settings.anthropic_provider_enabled,
    )
    anthropic_api_key = env_values.get("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    anthropic_base_url = env_values.get("ANTHROPIC_BASE_URL", settings.anthropic_base_url)
    anthropic_model = env_values.get("ANTHROPIC_MODEL", settings.anthropic_model)

    openrouter_enabled = _coerce_bool(
        env_values.get("OPENROUTER_PROVIDER_ENABLED"),
        settings.openrouter_provider_enabled,
    )
    openrouter_api_key = env_values.get("OPENROUTER_API_KEY", settings.openrouter_api_key)
    openrouter_base_url = env_values.get("OPENROUTER_BASE_URL", settings.openrouter_base_url)

    openai_configured = is_real_api_key_configured(openai_api_key)
    deepseek_configured = is_real_api_key_configured(deepseek_api_key)
    anthropic_configured = is_real_api_key_configured(anthropic_api_key)
    openrouter_configured = is_real_api_key_configured(openrouter_api_key)
    openai_effective = (
        cloud_enabled
        and validation_enabled
        and openai_enabled
        and openai_configured
    )
    deepseek_effective = (
        cloud_enabled
        and validation_enabled
        and deepseek_enabled
        and deepseek_configured
    )
    anthropic_effective = (
        cloud_enabled
        and validation_enabled
        and anthropic_enabled
        and anthropic_configured
    )
    openrouter_effective = (
        cloud_enabled
        and validation_enabled
        and openrouter_enabled
        and openrouter_configured
    )
    return {
        "env_file": str(env_path),
        "global": {
            "cloud_providers_enabled": cloud_enabled,
            "real_provider_validation_enabled": validation_enabled,
            "real_provider_max_cost_brl": max_cost_brl,
            "real_provider_timeout_seconds": timeout_seconds,
        },
        "providers": {
            "openai": {
                "enabled": openai_enabled,
                "effective_enabled": openai_effective,
                "configured": openai_configured,
                "masked_api_key": masked_real_api_key(openai_api_key),
                "base_url": openai_base_url or "https://api.openai.com/v1",
                "chat_model": openai_chat_model,
                "embeddings_model": openai_embeddings_model,
            },
            "deepseek": {
                "enabled": deepseek_enabled,
                "effective_enabled": deepseek_effective,
                "configured": deepseek_configured,
                "masked_api_key": masked_real_api_key(deepseek_api_key),
                "base_url": deepseek_base_url or "https://api.deepseek.com",
                "chat_model": deepseek_chat_model,
            },
            "anthropic": {
                "enabled": anthropic_enabled,
                "effective_enabled": anthropic_effective,
                "configured": anthropic_configured,
                "masked_api_key": masked_real_api_key(anthropic_api_key),
                "base_url": anthropic_base_url or "https://api.anthropic.com",
                "model": anthropic_model,
            },
            "openrouter": {
                "enabled": openrouter_enabled,
                "effective_enabled": openrouter_effective,
                "configured": openrouter_configured,
                "masked_api_key": masked_real_api_key(openrouter_api_key),
                "base_url": openrouter_base_url or "https://openrouter.ai/api/v1",
            },
        },
    }


def env_updates_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    global_cfg = payload.get("global", {})
    providers = payload.get("providers", {})
    updates = {
        "CLOUD_PROVIDERS_ENABLED": _bool_string(bool(global_cfg.get("cloud_providers_enabled"))),
        "REAL_PROVIDER_VALIDATION_ENABLED": _bool_string(bool(global_cfg.get("real_provider_validation_enabled"))),
        "REAL_PROVIDER_MAX_COST_BRL": str(global_cfg.get("real_provider_max_cost_brl", 2.0)),
        "REAL_PROVIDER_TIMEOUT_SECONDS": str(int(global_cfg.get("real_provider_timeout_seconds", 30))),
        "OPENAI_PROVIDER_ENABLED": _bool_string(bool(providers.get("openai", {}).get("enabled"))),
        "OPENAI_BASE_URL": str(providers.get("openai", {}).get("base_url", "")).strip(),
        "OPENAI_CHAT_MODEL": str(providers.get("openai", {}).get("chat_model", "")).strip(),
        "OPENAI_EMBEDDINGS_MODEL": str(providers.get("openai", {}).get("embeddings_model", "")).strip(),
        "DEEPSEEK_PROVIDER_ENABLED": _bool_string(bool(providers.get("deepseek", {}).get("enabled"))),
        "DEEPSEEK_BASE_URL": str(providers.get("deepseek", {}).get("base_url", "")).strip(),
        "DEEPSEEK_CHAT_MODEL": str(providers.get("deepseek", {}).get("chat_model", "")).strip(),
        "ANTHROPIC_PROVIDER_ENABLED": _bool_string(bool(providers.get("anthropic", {}).get("enabled"))),
        "ANTHROPIC_BASE_URL": str(providers.get("anthropic", {}).get("base_url", "")).strip(),
        "ANTHROPIC_MODEL": str(providers.get("anthropic", {}).get("model", "")).strip(),
        "OPENROUTER_PROVIDER_ENABLED": _bool_string(bool(providers.get("openrouter", {}).get("enabled"))),
        "OPENROUTER_BASE_URL": str(providers.get("openrouter", {}).get("base_url", "")).strip(),
    }

    for provider_key, env_key in [
        ("openai", "OPENAI_API_KEY"),
        ("deepseek", "DEEPSEEK_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ]:
        provider = providers.get(provider_key, {})
        if provider.get("clear_api_key"):
            updates[env_key] = ""
            continue
        api_key = provider.get("api_key")
        if isinstance(api_key, str) and api_key.strip():
            updates[env_key] = api_key.strip()

    return updates
