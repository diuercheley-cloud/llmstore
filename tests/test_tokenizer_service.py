import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock tiktoken and tokenizers before importing the service
mock_tiktoken = MagicMock()
sys.modules["tiktoken"] = mock_tiktoken
mock_tokenizers = MagicMock()
sys.modules["tokenizers"] = mock_tokenizers


# Ensure models are registered
from app.core.config import Settings
from app.services.tokenizer_service import TokenizerService


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("TOKEN_COUNTING_REAL_ENABLED", "False")
    return Settings(
        tokenizer_mode="auto",
        tokenizer_strict=False,
        tokenizer_cache_enabled=True
    )

@pytest.fixture(autouse=True)
def mock_settings(settings):
    with patch("app.services.tokenizer_service.get_settings", return_value=settings), \
         patch("app.services.token_counting.token_counter.get_settings", return_value=settings), \
         patch("app.core.config.get_settings", return_value=settings):
        yield

@pytest.fixture
def tokenizer_service(settings):
    return TokenizerService()

@pytest.mark.asyncio
async def test_count_text_tokens_tiktoken(tokenizer_service):
    # Mock tiktoken
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3] # 3 tokens
    
    with patch("tiktoken.encoding_for_model", return_value=mock_encoding):
        res = await tokenizer_service.count_text_tokens("hello world", model="gpt-3.5-turbo")
        assert res.input_tokens == 3
        assert res.method == "tiktoken"
        assert res.is_estimated is False

@pytest.mark.asyncio
async def test_count_text_tokens_fallback(tokenizer_service):
    # Model not starting with gpt- or similar
    res = await tokenizer_service.count_text_tokens("hello world", model="unknown-model")
    assert res.method == "estimated"
    assert res.is_estimated is True
    assert res.input_tokens > 0

@pytest.mark.asyncio
async def test_count_text_tokens_strict_failure(tokenizer_service):
    tokenizer_service.settings.tokenizer_strict = True
    # Should fail because it's not a tiktoken model and no HF configured
    with pytest.raises(RuntimeError, match="Strict tokenization enabled"):
        await tokenizer_service.count_text_tokens("hello world", model="unknown-model")

@pytest.mark.asyncio
async def test_count_chat_tokens_tiktoken(tokenizer_service):
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2] # 2 tokens per field
    
    with patch("tiktoken.encoding_for_model", return_value=mock_encoding):
        messages = [{"role": "user", "content": "hi"}]
        res = await tokenizer_service.count_chat_tokens(messages, model="gpt-3.5-turbo")
        assert res.method == "tiktoken"
        assert res.is_estimated is False
        # (4 for msg overhead + 2 for role + 2 for content + 2 for reply prefix) = 10
        assert res.input_tokens == 10

@pytest.mark.asyncio
async def test_count_embedding_tokens(tokenizer_service):
    res = await tokenizer_service.count_embedding_tokens(["hi", "there"], model="text-embedding-3-small")
    assert res.total_tokens > 0
    assert res.is_estimated is True # fallback since it's not gpt-

@pytest.mark.asyncio
async def test_usage_record_persistence(tokenizer_service, session):
    import uuid

    from app.models.client import Client
    from app.models.usage_record import UsageRecord
    from app.services.quota import record_usage
    from sqlalchemy import select

    client = Client(id=uuid.uuid4(), name="test")
    session.add(client)
    await session.commit()

    await record_usage(
        session, 
        client.id, 
        10, 
        20, 
        token_count_method="tiktoken", 
        tokens_estimated=False
    )
    await session.commit()

    result = await session.execute(select(UsageRecord).where(UsageRecord.client_id == client.id))
    record = result.scalars().first()
    assert record.token_count_method == "tiktoken"
    assert record.tokens_estimated is False
    assert record.prompt_tokens == 10
    assert record.completion_tokens == 20

@pytest.mark.asyncio
async def test_billing_record_request_financials(session):
    import uuid

    from app.models.client import Client
    from app.models.request_financial import RequestFinancial
    from app.services.billing.pricing_engine import record_request_financials
    from sqlalchemy import select

    client = Client(id=uuid.uuid4(), name="test_billing")
    session.add(client)
    await session.commit()

    record = await record_request_financials(
        session,
        client_id=client.id,
        endpoint_type="chat",
        provider="openai",
        model="gpt-4o",
        prompt_tokens=100,
        completion_tokens=50,
        token_count_method="tiktoken",
        tokens_estimated=False
    )
    await session.commit()

    result = await session.execute(select(RequestFinancial).where(RequestFinancial.id == record.id))
    saved = result.scalar_one()
    assert saved.token_count_method == "tiktoken"
    assert saved.tokens_estimated is False
    assert saved.prompt_tokens == 100
    assert saved.completion_tokens == 50
