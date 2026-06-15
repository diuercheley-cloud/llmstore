from typing import Any, Protocol, runtime_checkable

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel, Field


class ProviderCapabilities(ContractCapability):
    chat: bool = False
    streaming: bool = False
    responses: bool = False
    embeddings: bool = False
    tools: bool = False
    vision: bool = False
    json_mode: bool = False
    max_context_tokens: int = 0
    pricing_configured: bool = False


class ProviderRequest(BaseModel):
    model: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    id: str
    model: str
    choices: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class ProviderContract(BaseContract, Protocol):
    """
    Contract for LLM Providers (OpenAI, Anthropic, Local, etc.)
    """

    async def health_check(self) -> dict[str, Any]:
        """Returns health status of the provider."""
        ...

    async def list_models(self) -> list[str]:
        """Returns a list of supported model IDs."""
        ...

    async def chat_completion(self, request: ProviderRequest) -> ProviderResponse:
        """Executes a chat completion request."""
        ...

    async def embeddings(self, request: ProviderRequest) -> ProviderResponse:
        """Executes an embeddings request."""
        ...

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimates the cost of a request."""
        ...

    def capabilities(self) -> ProviderCapabilities:
        """Returns the capabilities supported by this provider."""
        ...

    def validate_contract(self) -> bool:
        # Check if all required methods are present
        required_methods = [
            "health_check",
            "list_models",
            "chat_completion",
            "embeddings",
            "estimate_cost",
            "capabilities",
        ]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
