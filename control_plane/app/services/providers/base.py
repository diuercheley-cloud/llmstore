import enum
from abc import ABC, abstractmethod
from typing import Any

from app.contracts.provider import (
    ProviderContract,
)
from app.services.providers.schemas import ProviderCapabilities


class ProviderType(str, enum.Enum):
    LOCAL = "local"
    LMSTUDIO = "lmstudio"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    BEDROCK = "bedrock"
    AZURE_OPENAI = "azure_openai"
    MISTRAL = "mistral"
    COHERE = "cohere"
    GROQ = "groq"
    TOGETHER = "together"
    PERPLEXITY = "perplexity"
    REPLICATE = "replicate"
    XAI = "xai"
    FIREWORKS = "fireworks"
    AI21 = "ai21"


class ProviderAdapter(ProviderContract, ABC):
    def __init__(self, provider_id: str, provider_type: ProviderType, enabled: bool, configured: bool):
        self._provider_id = provider_id
        self._provider_type = provider_type
        self._enabled = enabled
        self._configured = configured

    def validate_contract(self) -> bool:
        return True

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def configured(self) -> bool:
        return self._configured

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...

    @abstractmethod
    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    async def embeddings(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        ...

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        ...

    def mask_api_key(self, key: str | None) -> str | None:
        if not key:
            return None
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]
