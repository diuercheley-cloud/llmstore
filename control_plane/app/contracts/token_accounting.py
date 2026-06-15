from typing import Any, Protocol, runtime_checkable

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel


class TokenCountResult(BaseModel):
    input_tokens: int
    output_tokens: int | None = None
    total_tokens: int
    method: str
    model: str | None = None
    is_estimated: bool


class TokenAccountingCapabilities(ContractCapability):
    native_tiktoken: bool = False
    native_llama: bool = False
    hf_tokenizers: bool = False


@runtime_checkable
class TokenAccountingContract(BaseContract, Protocol):
    """
    Contract for Token Counting and Accounting.
    """

    async def count_text_tokens(self, text: str, model: str | None = None) -> TokenCountResult:
        """Counts tokens in a plain string."""
        ...

    async def count_chat_tokens(
        self, messages: list[dict[str, Any]], model: str | None = None
    ) -> TokenCountResult:
        """Counts tokens in a chat message history."""
        ...

    def capabilities(self) -> TokenAccountingCapabilities:
        """Returns tokenization capabilities."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["count_text_tokens", "count_chat_tokens", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
