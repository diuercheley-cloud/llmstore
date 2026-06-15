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
    "PROVIDERS_ENABLED",
    "REAL_PROVIDER_VALIDATION_ENABLED",
    "REAL_PROVIDER_MAX_COST_BRL",
    "REAL_PROVIDER_TIMEOUT_SECONDS",
    "PROVIDER_MAX_RETRIES",
    "PROVIDER_FAIL_CLOSED",
    "REAL_PROVIDER_LOG_PROMPTS",
    "REAL_PROVIDER_STORE_RESPONSES",
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
    "LMSTUDIO_ENABLED",
    "LMSTUDIO_BASE_URL",
    "LMSTUDIO_API_KEY",
    "LMSTUDIO_CHAT_MODEL",
    "GEMINI_PROVIDER_ENABLED",
    "GEMINI_API_KEY",
    "GEMINI_BASE_URL",
    "AZURE_OPENAI_PROVIDER_ENABLED",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
    "BEDROCK_PROVIDER_ENABLED",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "MISTRAL_PROVIDER_ENABLED",
    "MISTRAL_API_KEY",
    "COHERE_PROVIDER_ENABLED",
    "COHERE_API_KEY",
    "GROQ_PROVIDER_ENABLED",
    "GROQ_API_KEY",
    "TOGETHER_PROVIDER_ENABLED",
    "TOGETHER_API_KEY",
    "PERPLEXITY_PROVIDER_ENABLED",
    "PERPLEXITY_API_KEY",
    "REPLICATE_PROVIDER_ENABLED",
    "REPLICATE_API_KEY",
    "XAI_PROVIDER_ENABLED",
    "XAI_API_KEY",
    "FIREWORKS_PROVIDER_ENABLED",
    "FIREWORKS_API_KEY",
    "AI21_PROVIDER_ENABLED",
    "AI21_API_KEY",
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

    providers_enabled = env_values.get("PROVIDERS_ENABLED", settings.providers_enabled)
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
    provider_max_retries = _coerce_int(
        env_values.get("PROVIDER_MAX_RETRIES"),
        settings.provider_max_retries,
    )
    provider_fail_closed = _coerce_bool(
        env_values.get("PROVIDER_FAIL_CLOSED"),
        settings.provider_fail_closed,
    )
    log_prompts = _coerce_bool(
        env_values.get("REAL_PROVIDER_LOG_PROMPTS"),
        settings.real_provider_log_prompts,
    )
    store_responses = _coerce_bool(
        env_values.get("REAL_PROVIDER_STORE_RESPONSES"),
        settings.real_provider_store_responses,
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

    lmstudio_enabled = _coerce_bool(
        env_values.get("LMSTUDIO_ENABLED"),
        settings.lmstudio_enabled,
    )
    lmstudio_base_url = env_values.get("LMSTUDIO_BASE_URL", settings.lmstudio_base_url)
    lmstudio_api_key = env_values.get("LMSTUDIO_API_KEY", settings.lmstudio_api_key)
    lmstudio_chat_model = env_values.get("LMSTUDIO_CHAT_MODEL", settings.lmstudio_chat_model)

    gemini_enabled = _coerce_bool(
        env_values.get("GEMINI_PROVIDER_ENABLED"),
        settings.gemini_provider_enabled,
    )
    gemini_api_key = env_values.get("GEMINI_API_KEY", settings.gemini_api_key)
    gemini_base_url = env_values.get("GEMINI_BASE_URL", settings.gemini_base_url)

    azure_openai_enabled = _coerce_bool(
        env_values.get("AZURE_OPENAI_PROVIDER_ENABLED"),
        settings.azure_openai_provider_enabled,
    )
    azure_openai_api_key = env_values.get("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key)
    azure_openai_endpoint = env_values.get("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint)
    azure_openai_api_version = env_values.get(
        "AZURE_OPENAI_API_VERSION", settings.azure_openai_api_version
    )
    azure_openai_deployment = env_values.get(
        "AZURE_OPENAI_DEPLOYMENT", settings.azure_openai_deployment
    )

    bedrock_enabled = _coerce_bool(
        env_values.get("BEDROCK_PROVIDER_ENABLED"),
        settings.bedrock_provider_enabled,
    )
    aws_access_key_id = env_values.get("AWS_ACCESS_KEY_ID", settings.aws_access_key_id)
    aws_secret_access_key = env_values.get("AWS_SECRET_ACCESS_KEY", settings.aws_secret_access_key)
    aws_region = env_values.get("AWS_REGION", settings.aws_region)

    mistral_enabled = _coerce_bool(
        env_values.get("MISTRAL_PROVIDER_ENABLED"),
        settings.mistral_provider_enabled,
    )
    mistral_api_key = env_values.get("MISTRAL_API_KEY", settings.mistral_api_key)

    cohere_enabled = _coerce_bool(
        env_values.get("COHERE_PROVIDER_ENABLED"),
        settings.cohere_provider_enabled,
    )
    cohere_api_key = env_values.get("COHERE_API_KEY", settings.cohere_api_key)

    groq_enabled = _coerce_bool(
        env_values.get("GROQ_PROVIDER_ENABLED"),
        settings.groq_provider_enabled,
    )
    groq_api_key = env_values.get("GROQ_API_KEY", settings.groq_api_key)

    together_enabled = _coerce_bool(
        env_values.get("TOGETHER_PROVIDER_ENABLED"),
        settings.together_provider_enabled,
    )
    together_api_key = env_values.get("TOGETHER_API_KEY", settings.together_api_key)

    perplexity_enabled = _coerce_bool(
        env_values.get("PERPLEXITY_PROVIDER_ENABLED"),
        settings.perplexity_provider_enabled,
    )
    perplexity_api_key = env_values.get("PERPLEXITY_API_KEY", settings.perplexity_api_key)

    replicate_enabled = _coerce_bool(
        env_values.get("REPLICATE_PROVIDER_ENABLED"),
        settings.replicate_provider_enabled,
    )
    replicate_api_key = env_values.get("REPLICATE_API_KEY", settings.replicate_api_key)

    xai_enabled = _coerce_bool(
        env_values.get("XAI_PROVIDER_ENABLED"),
        settings.xai_provider_enabled,
    )
    xai_api_key = env_values.get("XAI_API_KEY", settings.xai_api_key)

    fireworks_enabled = _coerce_bool(
        env_values.get("FIREWORKS_PROVIDER_ENABLED"),
        settings.fireworks_provider_enabled,
    )
    fireworks_api_key = env_values.get("FIREWORKS_API_KEY", settings.fireworks_api_key)

    ai21_enabled = _coerce_bool(
        env_values.get("AI21_PROVIDER_ENABLED"),
        settings.ai21_provider_enabled,
    )
    ai21_api_key = env_values.get("AI21_API_KEY", settings.ai21_api_key)

    openai_configured = is_real_api_key_configured(openai_api_key)
    deepseek_configured = is_real_api_key_configured(deepseek_api_key)
    anthropic_configured = is_real_api_key_configured(anthropic_api_key)
    openrouter_configured = is_real_api_key_configured(openrouter_api_key)
    lmstudio_configured = bool(lmstudio_base_url.strip())
    gemini_configured = is_real_api_key_configured(gemini_api_key)
    azure_openai_configured = bool(azure_openai_api_key and azure_openai_endpoint)
    bedrock_configured = bool(aws_access_key_id and aws_secret_access_key)
    mistral_configured = is_real_api_key_configured(mistral_api_key)
    cohere_configured = is_real_api_key_configured(cohere_api_key)
    groq_configured = is_real_api_key_configured(groq_api_key)
    together_configured = is_real_api_key_configured(together_api_key)
    perplexity_configured = is_real_api_key_configured(perplexity_api_key)
    replicate_configured = is_real_api_key_configured(replicate_api_key)
    xai_configured = is_real_api_key_configured(xai_api_key)
    fireworks_configured = is_real_api_key_configured(fireworks_api_key)
    ai21_configured = is_real_api_key_configured(ai21_api_key)
    openai_effective = cloud_enabled and validation_enabled and openai_enabled and openai_configured
    deepseek_effective = (
        cloud_enabled and validation_enabled and deepseek_enabled and deepseek_configured
    )
    anthropic_effective = (
        cloud_enabled and validation_enabled and anthropic_enabled and anthropic_configured
    )
    openrouter_effective = (
        cloud_enabled and validation_enabled and openrouter_enabled and openrouter_configured
    )
    lmstudio_effective = lmstudio_enabled and lmstudio_configured
    return {
        "env_file": str(env_path),
        "global": {
            "providers_enabled": providers_enabled,
            "cloud_providers_enabled": cloud_enabled,
            "real_provider_validation_enabled": validation_enabled,
            "real_provider_max_cost_brl": max_cost_brl,
            "real_provider_timeout_seconds": timeout_seconds,
            "provider_max_retries": provider_max_retries,
            "provider_fail_closed": provider_fail_closed,
            "real_provider_log_prompts": log_prompts,
            "real_provider_store_responses": store_responses,
        },
        "providers": {
            "lmstudio": {
                "enabled": lmstudio_enabled,
                "effective_enabled": lmstudio_effective,
                "configured": lmstudio_configured,
                "masked_api_key": masked_real_api_key(lmstudio_api_key),
                "base_url": lmstudio_base_url,
                "chat_model": lmstudio_chat_model,
            },
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
            "gemini": {
                "enabled": gemini_enabled,
                "effective_enabled": cloud_enabled
                and validation_enabled
                and gemini_enabled
                and gemini_configured,
                "configured": gemini_configured,
                "masked_api_key": masked_real_api_key(gemini_api_key),
                "base_url": gemini_base_url or "https://generativelanguage.googleapis.com/v1beta",
            },
            "azure_openai": {
                "enabled": azure_openai_enabled,
                "effective_enabled": cloud_enabled
                and validation_enabled
                and azure_openai_enabled
                and azure_openai_configured,
                "configured": azure_openai_configured,
                "masked_api_key": masked_real_api_key(azure_openai_api_key),
                "endpoint": azure_openai_endpoint,
                "api_version": azure_openai_api_version,
                "deployment": azure_openai_deployment,
            },
            "bedrock": {
                "enabled": bedrock_enabled,
                "effective_enabled": cloud_enabled
                and validation_enabled
                and bedrock_enabled
                and bedrock_configured,
                "configured": bedrock_configured,
                "masked_aws_access_key_id": _mask(aws_access_key_id),
                "masked_aws_secret_access_key": _mask(aws_secret_access_key),
                "region": aws_region,
            },
            "mistral": {
                "enabled": mistral_enabled,
                "effective_enabled": cloud_enabled and mistral_enabled and mistral_configured,
                "configured": mistral_configured,
                "masked_api_key": masked_real_api_key(mistral_api_key),
            },
            "cohere": {
                "enabled": cohere_enabled,
                "effective_enabled": cloud_enabled and cohere_enabled and cohere_configured,
                "configured": cohere_configured,
                "masked_api_key": masked_real_api_key(cohere_api_key),
            },
            "groq": {
                "enabled": groq_enabled,
                "effective_enabled": cloud_enabled and groq_enabled and groq_configured,
                "configured": groq_configured,
                "masked_api_key": masked_real_api_key(groq_api_key),
            },
            "together": {
                "enabled": together_enabled,
                "effective_enabled": cloud_enabled and together_enabled and together_configured,
                "configured": together_configured,
                "masked_api_key": masked_real_api_key(together_api_key),
            },
            "perplexity": {
                "enabled": perplexity_enabled,
                "effective_enabled": cloud_enabled and perplexity_enabled and perplexity_configured,
                "configured": perplexity_configured,
                "masked_api_key": masked_real_api_key(perplexity_api_key),
            },
            "replicate": {
                "enabled": replicate_enabled,
                "effective_enabled": cloud_enabled and replicate_enabled and replicate_configured,
                "configured": replicate_configured,
                "masked_api_key": masked_real_api_key(replicate_api_key),
            },
            "xai": {
                "enabled": xai_enabled,
                "effective_enabled": cloud_enabled and xai_enabled and xai_configured,
                "configured": xai_configured,
                "masked_api_key": masked_real_api_key(xai_api_key),
            },
            "fireworks": {
                "enabled": fireworks_enabled,
                "effective_enabled": cloud_enabled and fireworks_enabled and fireworks_configured,
                "configured": fireworks_configured,
                "masked_api_key": masked_real_api_key(fireworks_api_key),
            },
            "ai21": {
                "enabled": ai21_enabled,
                "effective_enabled": cloud_enabled and ai21_enabled and ai21_configured,
                "configured": ai21_configured,
                "masked_api_key": masked_real_api_key(ai21_api_key),
            },
        },
    }


def env_updates_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    settings = get_settings()
    global_cfg = payload.get("global", {})
    providers = payload.get("providers", {})
    updates = {
        "PROVIDERS_ENABLED": str(
            global_cfg.get("providers_enabled", settings.providers_enabled)
        ).strip(),
        "CLOUD_PROVIDERS_ENABLED": _bool_string(bool(global_cfg.get("cloud_providers_enabled"))),
        "REAL_PROVIDER_VALIDATION_ENABLED": _bool_string(
            bool(global_cfg.get("real_provider_validation_enabled"))
        ),
        "REAL_PROVIDER_MAX_COST_BRL": str(global_cfg.get("real_provider_max_cost_brl", 2.0)),
        "REAL_PROVIDER_TIMEOUT_SECONDS": str(
            int(global_cfg.get("real_provider_timeout_seconds", 30))
        ),
        "PROVIDER_MAX_RETRIES": str(int(global_cfg.get("provider_max_retries", 2))),
        "PROVIDER_FAIL_CLOSED": _bool_string(bool(global_cfg.get("provider_fail_closed", True))),
        "REAL_PROVIDER_LOG_PROMPTS": _bool_string(
            bool(global_cfg.get("real_provider_log_prompts", False))
        ),
        "REAL_PROVIDER_STORE_RESPONSES": _bool_string(
            bool(global_cfg.get("real_provider_store_responses", False))
        ),
        "LMSTUDIO_ENABLED": _bool_string(bool(providers.get("lmstudio", {}).get("enabled"))),
        "LMSTUDIO_BASE_URL": str(providers.get("lmstudio", {}).get("base_url", "")).strip(),
        "LMSTUDIO_CHAT_MODEL": str(providers.get("lmstudio", {}).get("chat_model", "")).strip(),
        "OPENAI_PROVIDER_ENABLED": _bool_string(bool(providers.get("openai", {}).get("enabled"))),
        "OPENAI_BASE_URL": str(providers.get("openai", {}).get("base_url", "")).strip(),
        "OPENAI_CHAT_MODEL": str(providers.get("openai", {}).get("chat_model", "")).strip(),
        "OPENAI_EMBEDDINGS_MODEL": str(
            providers.get("openai", {}).get("embeddings_model", "")
        ).strip(),
        "DEEPSEEK_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("deepseek", {}).get("enabled"))
        ),
        "DEEPSEEK_BASE_URL": str(providers.get("deepseek", {}).get("base_url", "")).strip(),
        "DEEPSEEK_CHAT_MODEL": str(providers.get("deepseek", {}).get("chat_model", "")).strip(),
        "ANTHROPIC_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("anthropic", {}).get("enabled"))
        ),
        "ANTHROPIC_BASE_URL": str(providers.get("anthropic", {}).get("base_url", "")).strip(),
        "ANTHROPIC_MODEL": str(providers.get("anthropic", {}).get("model", "")).strip(),
        "OPENROUTER_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("openrouter", {}).get("enabled"))
        ),
        "OPENROUTER_BASE_URL": str(providers.get("openrouter", {}).get("base_url", "")).strip(),
        "GEMINI_PROVIDER_ENABLED": _bool_string(bool(providers.get("gemini", {}).get("enabled"))),
        "GEMINI_BASE_URL": str(providers.get("gemini", {}).get("base_url", "")).strip(),
        "AZURE_OPENAI_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("azure_openai", {}).get("enabled"))
        ),
        "AZURE_OPENAI_ENDPOINT": str(providers.get("azure_openai", {}).get("endpoint", "")).strip(),
        "AZURE_OPENAI_API_VERSION": str(
            providers.get("azure_openai", {}).get("api_version", "")
        ).strip(),
        "AZURE_OPENAI_DEPLOYMENT": str(
            providers.get("azure_openai", {}).get("deployment", "")
        ).strip(),
        "BEDROCK_PROVIDER_ENABLED": _bool_string(bool(providers.get("bedrock", {}).get("enabled"))),
        "AWS_REGION": str(providers.get("bedrock", {}).get("region", "")).strip(),
        "MISTRAL_PROVIDER_ENABLED": _bool_string(bool(providers.get("mistral", {}).get("enabled"))),
        "COHERE_PROVIDER_ENABLED": _bool_string(bool(providers.get("cohere", {}).get("enabled"))),
        "GROQ_PROVIDER_ENABLED": _bool_string(bool(providers.get("groq", {}).get("enabled"))),
        "TOGETHER_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("together", {}).get("enabled"))
        ),
        "PERPLEXITY_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("perplexity", {}).get("enabled"))
        ),
        "REPLICATE_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("replicate", {}).get("enabled"))
        ),
        "XAI_PROVIDER_ENABLED": _bool_string(bool(providers.get("xai", {}).get("enabled"))),
        "FIREWORKS_PROVIDER_ENABLED": _bool_string(
            bool(providers.get("fireworks", {}).get("enabled"))
        ),
        "AI21_PROVIDER_ENABLED": _bool_string(bool(providers.get("ai21", {}).get("enabled"))),
    }

    provider_secret_keys = {
        "lmstudio": [("api_key", "LMSTUDIO_API_KEY")],
        "openai": [("api_key", "OPENAI_API_KEY")],
        "deepseek": [("api_key", "DEEPSEEK_API_KEY")],
        "anthropic": [("api_key", "ANTHROPIC_API_KEY")],
        "openrouter": [("api_key", "OPENROUTER_API_KEY")],
        "gemini": [("api_key", "GEMINI_API_KEY")],
        "azure_openai": [("api_key", "AZURE_OPENAI_API_KEY")],
        "bedrock": [
            ("aws_access_key_id", "AWS_ACCESS_KEY_ID"),
            ("aws_secret_access_key", "AWS_SECRET_ACCESS_KEY"),
        ],
        "mistral": [("api_key", "MISTRAL_API_KEY")],
        "cohere": [("api_key", "COHERE_API_KEY")],
        "groq": [("api_key", "GROQ_API_KEY")],
        "together": [("api_key", "TOGETHER_API_KEY")],
        "perplexity": [("api_key", "PERPLEXITY_API_KEY")],
        "replicate": [("api_key", "REPLICATE_API_KEY")],
        "xai": [("api_key", "XAI_API_KEY")],
        "fireworks": [("api_key", "FIREWORKS_API_KEY")],
        "ai21": [("api_key", "AI21_API_KEY")],
    }

    for provider_key, mappings in provider_secret_keys.items():
        provider = providers.get(provider_key, {})
        for field, env_key in mappings:
            if (
                provider.get(f"clear_{field}")
                or provider.get("clear_api_key")
                and field == "api_key"
            ):
                updates[env_key] = ""
                continue
            value = provider.get(field)
            if isinstance(value, str) and value.strip():
                updates[env_key] = value.strip()

    return updates
