import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.request_financial import RequestFinancial
from app.services.billing.pricing_engine import (
    record_request_financials,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_local() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_request_financials(session):
    record = await record_request_financials(
        session,
        client_id="test-client",
        endpoint_type="chat",
        provider="local",
        model="gemma",
        prompt_tokens=100,
        completion_tokens=50,
        cache_hit=False,
        latency_ms=150,
        plan_code="basic",
        requested_model="gemma",
        resolved_model="gemma",
        api_key_prefix="test-prefix",
    )
    assert record.id is not None
    assert record.client_id == "test-client"
    assert record.provider == "local"
    assert record.prompt_tokens == 100
    assert record.completion_tokens == 50
    assert record.total_tokens == 150
    assert record.cache_hit is False
    assert record.latency_ms == 150
    assert record.pricing_rule_id == "plan:basic"


@pytest.mark.asyncio
async def test_record_financials_with_cache(session):
    no_cache = await record_request_financials(
        session, client_id="c1", endpoint_type="chat", provider="local",
        model="m", prompt_tokens=100, completion_tokens=50,
        cache_hit=False, plan_code="basic",
    )
    cached = await record_request_financials(
        session, client_id="c1", endpoint_type="chat", provider="local",
        model="m", prompt_tokens=100, completion_tokens=50,
        cache_hit=True, plan_code="basic",
    )
    assert cached.customer_price_brl <= no_cache.customer_price_brl


@pytest.mark.asyncio
async def test_record_financials_calculates_margin(session):
    record = await record_request_financials(
        session, client_id="c1", endpoint_type="chat", provider="local",
        model="m", prompt_tokens=1000, completion_tokens=500,
        plan_code="basic",
    )
    assert record.gross_profit_brl is not None
    assert record.margin_percent is not None or record.gross_profit_brl == 0


@pytest.mark.asyncio
async def test_record_financials_no_secrets(session):
    record = await record_request_financials(
        session, client_id="c1", endpoint_type="chat", provider="local",
        model="m", prompt_tokens=10, completion_tokens=5,
    )
    dump = str(record.__dict__)
    assert "api_key" not in dump.lower() or "api_key_prefix" in dump
    assert "secret" not in dump.lower()


@pytest.mark.asyncio
async def test_multiple_records(session):
    for i in range(5):
        await record_request_financials(
            session, client_id=f"c{i}", endpoint_type="chat",
            provider="local", model="m", prompt_tokens=100, completion_tokens=50,
        )
    import sqlalchemy as sa
    result = await session.execute(sa.select(sa.func.count()).select_from(RequestFinancial))
    count = result.scalar()
    assert count == 5
