import pytest
from app.contracts.token_accounting import (
    TokenAccountingCapabilities,
    TokenAccountingContract,
    TokenCountResult,
)


class MockTokenizer(TokenAccountingContract):
    async def count_text_tokens(self, text: str, model: str = None) -> TokenCountResult:
        count = len(text.split())
        return TokenCountResult(input_tokens=count, total_tokens=count, method="mock", is_estimated=True)

    async def count_chat_tokens(self, messages: list, model: str = None) -> TokenCountResult:
        return TokenCountResult(input_tokens=10, total_tokens=10, method="mock", is_estimated=True)

    def capabilities(self) -> TokenAccountingCapabilities:
        return TokenAccountingCapabilities(native_tiktoken=True)

    def validate_contract(self) -> bool:
        return True

@pytest.mark.asyncio
async def test_token_accounting_contract_implementation():
    tokenizer = MockTokenizer()
    assert tokenizer.validate_contract() is True
    
    res = await tokenizer.count_text_tokens("hello world")
    assert res.input_tokens == 2
    assert res.method == "mock"
    
    caps = tokenizer.capabilities()
    assert caps.native_tiktoken is True
