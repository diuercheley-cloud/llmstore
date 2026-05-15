from __future__ import annotations

_PROVIDER_ALIASES = {
    "llamacpp": "llama.cpp",
    "llama_cpp": "llama.cpp",
    "openai-compatible": "openai_compatible",
    "openai compatible": "openai_compatible",
}

CLOUD_PROVIDER_IDS = frozenset({
    "openai",
    "anthropic",
    "deepseek",
    "openrouter",
})

LOCAL_PROVIDER_IDS = frozenset({
    "local",
    "lmstudio",
    "llama.cpp",
    "ollama",
    "vllm",
    "openai_compatible",
    "mock",
    "pocket",
    "pocket-tts",
})


def normalize_provider_name(provider_name: str | None) -> str:
    normalized = (provider_name or "").strip().lower()
    return _PROVIDER_ALIASES.get(normalized, normalized)


def is_cloud_provider(provider_name: str | None) -> bool:
    return normalize_provider_name(provider_name) in CLOUD_PROVIDER_IDS


def is_local_provider(provider_name: str | None) -> bool:
    return normalize_provider_name(provider_name) in LOCAL_PROVIDER_IDS


def classify_provider(provider_name: str | None) -> str:
    if is_cloud_provider(provider_name):
        return "cloud"
    if is_local_provider(provider_name):
        return "local"
    return "unknown"
