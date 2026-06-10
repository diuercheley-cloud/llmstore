from typing import Any, Dict, List

import pytest
from app.contracts.provider import (
    ProviderCapabilities,
    ProviderContract,
    ProviderRequest,
    ProviderResponse,
)


class MockProvider(ProviderContract):
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "ok"}

    async def list_models(self) -> List[str]:
        return ["model-1"]

    async def chat_completion(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(id="1", model=request.model, choices=[{"text": "hello"}])

    async def embeddings(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(id="2", model=request.model, usage={"tokens": 10})

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.01

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(chat=True)

    def validate_contract(self) -> bool:
        return True

@pytest.mark.asyncio
async def test_provider_contract_implementation():
    provider = MockProvider()
    assert provider.validate_contract() is True
    
    request = ProviderRequest(model="test-model", payload={"messages": []})
    response = await provider.chat_completion(request)
    assert response.id == "1"
    assert response.model == "test-model"
    
    caps = provider.capabilities()
    assert caps.chat is True
    assert caps.streaming is False

def test_provider_contract_runtime_check():
    assert isinstance(MockProvider(), ProviderContract)
