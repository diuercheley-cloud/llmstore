import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.services.billing.pricing_engine import (
    calculate_customer_price,
    calculate_financials,
    calculate_margin,
    estimate_provider_cost,
    record_request_financials,
)


@pytest.mark.asyncio
async def test_cache_hit_records_cache_hit_true(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    testing_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session() as session:
        record = await record_request_financials(
            session,
            client_id=str(uuid.uuid4()),
            endpoint_type="chat",
            provider="local",
            model="gemma",
            prompt_tokens=100,
            completion_tokens=50,
            cache_hit=True,
        )
        assert record.cache_hit is True

    await engine.dispose()


def test_cache_hit_provider_cost_zero():
    result = estimate_provider_cost("local", 0, 0)
    assert result.cost_usd == 0.0
    assert result.cost_brl == 0.0


def test_cache_hit_customer_price_discounted():
    price_no_cache = calculate_customer_price("basic", 1000, 500, cache_hit=False)
    price_cache = calculate_customer_price("basic", 1000, 500, cache_hit=True)
    assert price_cache.price_brl < price_no_cache.price_brl


def test_cache_hit_margin_calculation():
    financials = calculate_financials("local", 1000, 500, cache_hit=True, plan_code="basic")
    assert financials["cache_hit"] is True
    assert financials["margin_percent"] is not None
    assert financials["gross_profit_brl"] is not None
