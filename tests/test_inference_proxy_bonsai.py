import pytest
from unittest.mock import MagicMock
from app.services.inference_proxy import InferenceProxy
from app.core.config import Settings

@pytest.mark.asyncio
async def test_inference_proxy_prepares_payload_with_bonsai_fallback():
    settings = Settings(
        ADMIN_TOKEN="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost",
        DATA_PLANE_BASE_URL="http://localhost:8081",
        BONSAI_CHAT_TEMPLATE="chatml"
    )
    
    proxy = InferenceProxy(queue_manager=MagicMock(), circuit_breaker=MagicMock())
    proxy.settings = settings
    
    payload = {
        "model": "bonsai",
        "messages": [{"role": "user", "content": "hi"}]
    }
    
    # We can test _prepare_chat_payload directly
    prepared = proxy._prepare_chat_payload(
        payload,
        include_reasoning=False,
        backend="llama.cpp",
        prompt_template="qwen"
    )
    
    assert "chat_template" in prepared
    assert "<|im_end|>" in prepared["chat_template"]
