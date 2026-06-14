import pytest
import uuid
from app.services.audit import log_request
from app.models.core.request_log import RequestLog
from sqlalchemy import select

@pytest.mark.asyncio
async def test_log_request_persists_token_metrics(session):
    # Setup
    client_id = uuid.uuid4()
    
    # Execute
    request_log = await log_request(
        session,
        client_id=client_id,
        model="test-model",
        endpoint="/v1/test",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=100,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.001,
        backend_name="test-backend",
        attempts=1,
        fallback_used=False,
        cache_hit=False,
        token_count_method="tiktoken",
        tokens_estimated=False
    )
    
    # Verify in-memory object
    assert request_log.token_count_method == "tiktoken"
    assert request_log.tokens_estimated is False
    
    # Flush and verify from DB
    await session.flush()
    await session.refresh(request_log)
    
    result = await session.execute(
        select(RequestLog).where(RequestLog.id == request_log.id)
    )
    db_log = result.scalar_one()
    
    assert db_log.token_count_method == "tiktoken"
    assert db_log.tokens_estimated is False

@pytest.mark.asyncio
async def test_log_request_defaults_token_metrics(session):
    # Setup
    client_id = uuid.uuid4()
    
    # Execute with defaults
    request_log = await log_request(
        session,
        client_id=client_id,
        model="test-model",
        endpoint="/v1/test",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=100,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.001,
        backend_name="test-backend",
        attempts=1,
        fallback_used=False,
        cache_hit=False
    )
    
    # Verify defaults
    assert request_log.token_count_method is None
    assert request_log.tokens_estimated is True
    
    # Verify None handling for tokens_estimated
    request_log_none = await log_request(
        session,
        client_id=client_id,
        model="test-model",
        endpoint="/v1/test",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=100,
        status_code=200,
        is_stream=False,
        estimated_cost_usd=0.001,
        backend_name="test-backend",
        attempts=1,
        fallback_used=False,
        cache_hit=False,
        tokens_estimated=None
    )
    assert request_log_none.tokens_estimated is True
