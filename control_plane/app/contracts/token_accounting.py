from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable
from pydantic import BaseModel, Field
from app.contracts.base import BaseContract, ContractCapability

class TokenCountResult(BaseModel):
    input_tokens: int
    output_tokens: Optional[int] = None
    total_tokens: int
    method: str
    model: Optional[str] = None
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
    
    async def count_text_tokens(self, text: str, model: Optional[str] = None) -> TokenCountResult:
        """Counts tokens in a plain string."""
        ...

    async def count_chat_tokens(self, messages: List[Dict[str, Any]], model: Optional[str] = None) -> TokenCountResult:
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
