import logging

from app.core.config import get_settings
from app.services.providers.base import ProviderAdapter
from app.services.providers.schemas import (
    ProviderCapabilities,
    ProviderHealth,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

_providers: dict[str, ProviderAdapter] = {}
_registry_initialized = False


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def get_providers() -> dict[str, ProviderAdapter]:
    global _registry_initialized
    if not _registry_initialized:
        _init_registry()
    return dict(_providers)


def get_provider(provider_id: str) -> ProviderAdapter | None:
    return get_providers().get(provider_id)


def reload_registry() -> None:
    global _registry_initialized
    _registry_initialized = False
    _providers.clear()
    get_providers()


def _init_registry() -> None:
    global _registry_initialized
    if _registry_initialized:
        return

    from app.services.providers.ai21_provider import AI21Provider
    from app.services.providers.anthropic_provider import AnthropicProvider
    from app.services.providers.azure_openai_provider import AzureOpenAIProvider
    from app.services.providers.bedrock_provider import BedrockProvider
    from app.services.providers.cohere_provider import CohereProvider
    from app.services.providers.deepseek_provider import DeepSeekProvider
    from app.services.providers.fireworks_provider import FireworksProvider
    from app.services.providers.gemini_provider import GeminiProvider
    from app.services.providers.groq_provider import GroqProvider
    from app.services.providers.lmstudio_provider import LMStudioProvider
    from app.services.providers.local_provider import LocalProvider
    from app.services.providers.mistral_provider import MistralProvider
    from app.services.providers.openai_provider import OpenAIProvider
    from app.services.providers.openrouter_provider import OpenRouterProvider
    from app.services.providers.perplexity_provider import PerplexityProvider
    from app.services.providers.replicate_provider import ReplicateProvider
    from app.services.providers.together_provider import TogetherProvider
    from app.services.providers.xai_provider import XAIProvider

    settings = get_settings()
    providers_enabled = [p.strip() for p in settings.providers_enabled.split(",") if p.strip()]
    cloud_enabled = settings.cloud_providers_enabled

    all_providers: list[ProviderAdapter] = [
        LocalProvider(),
        LMStudioProvider(),
        OpenAIProvider(),
        AnthropicProvider(),
        DeepSeekProvider(),
        OpenRouterProvider(),
        GeminiProvider(),
        BedrockProvider(),
        AzureOpenAIProvider(),
        MistralProvider(),
        CohereProvider(),
        GroqProvider(),
        TogetherProvider(),
        PerplexityProvider(),
        ReplicateProvider(),
        XAIProvider(),
        FireworksProvider(),
        AI21Provider(),
    ]

    for p in all_providers:
        provider_id = p.provider_id
        is_cloud = p.provider_type.value in (
            "openai",
            "anthropic",
            "deepseek",
            "openrouter",
            "gemini",
            "bedrock",
            "azure_openai",
            "mistral",
            "cohere",
            "groq",
            "together",
            "perplexity",
            "replicate",
            "xai",
            "fireworks",
            "ai21",
        )

        # Always register all providers so admin can see them even when disabled
        if provider_id not in providers_enabled and not is_cloud:
            continue

        # Provider adapters expose `enabled` as a read-only property.
        # Keep them registered for observability/admin views, but leave their
        # own constructor-derived enabled state intact.
        if is_cloud and not cloud_enabled and not p.configured:
            logger.debug(
                "Cloud provider '%s' disabled (cloud_enabled=%s, configured=%s)",
                provider_id,
                cloud_enabled,
                p.configured,
            )
        elif is_cloud and cloud_enabled and not p.configured:
            logger.debug(
                "Cloud provider '%s' enabled but API key missing (configured=%s)",
                provider_id,
                p.configured,
            )

        _providers[provider_id] = p

    _registry_initialized = True


def get_all_provider_statuses() -> list[ProviderStatus]:
    statuses: list[ProviderStatus] = []
    for p in get_providers().values():
        caps = p.capabilities()
        models = ["<runtime>"]
        try:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    pass
            except RuntimeError:
                pass
        except Exception:
            pass
        statuses.append(
            ProviderStatus(
                provider_id=p.provider_id,
                provider_type=p.provider_type.value,
                enabled=p.enabled,
                configured=p.configured,
                healthy=None,
                capabilities=caps,
                models=models,
            )
        )
    return statuses


async def get_all_provider_health() -> list[ProviderHealth]:
    results: list[ProviderHealth] = []
    for p in get_providers().values():
        try:
            h = await p.health_check()
            last_error = h.get("error")
            if last_error and (
                "disabled" in str(last_error).lower() or "not configured" in str(last_error).lower()
            ):
                sanitized = str(last_error)
            elif last_error:
                sanitized = "health check failed"
            else:
                sanitized = None
            results.append(
                ProviderHealth(
                    provider_id=p.provider_id,
                    enabled=p.enabled,
                    configured=p.configured,
                    healthy=h.get("healthy"),
                    last_error_sanitized=sanitized,
                    latency_ms=h.get("latency_ms"),
                )
            )
        except Exception:
            results.append(
                ProviderHealth(
                    provider_id=p.provider_id,
                    enabled=p.enabled,
                    configured=p.configured,
                    healthy=False,
                    last_error_sanitized="health check error",
                )
            )
    return results


async def get_global_capabilities() -> dict[str, ProviderCapabilities]:
    return {p.provider_id: p.capabilities() for p in get_providers().values()}


def get_enabled_configured_providers() -> list[ProviderAdapter]:
    return [p for p in get_providers().values() if p.enabled and p.configured]
