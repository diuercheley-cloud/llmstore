from decimal import Decimal

import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.billing.wallet_service import (
    adjustment,
    credit_manual,
    ensure_idempotency,
    get_balance,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def fake_client_id():
    import uuid
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_credit(db_session, fake_client_id):
    key = "idem-credit-001"
    tx1 = await credit_manual(db_session, fake_client_id, Decimal("100.0000"), reason="first", idempotency_key=key)
    await db_session.commit()
    balance_after_first = await get_balance(db_session, fake_client_id)
    tx2 = await credit_manual(db_session, fake_client_id, Decimal("200.0000"), reason="second", idempotency_key=key)
    await db_session.commit()
    balance_after_second = await get_balance(db_session, fake_client_id)
    assert tx1.id == tx2.id
    assert tx1.amount_brl == tx2.amount_brl
    assert balance_after_first["balance_brl"] == 100.0
    assert balance_after_second["balance_brl"] == 100.0


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_adjustment(db_session, fake_client_id):
    key = "idem-adjust-001"
    tx1 = await adjustment(db_session, fake_client_id, Decimal("50.0000"), reason="bonus", idempotency_key=key)
    await db_session.commit()
    balance_after_first = await get_balance(db_session, fake_client_id)
    tx2 = await adjustment(db_session, fake_client_id, Decimal("999.0000"), reason="hacker", idempotency_key=key)
    await db_session.commit()
    balance_after_second = await get_balance(db_session, fake_client_id)
    assert tx1.id == tx2.id
    assert balance_after_first["balance_brl"] == 50.0
    assert balance_after_second["balance_brl"] == 50.0


@pytest.mark.asyncio
async def test_ensure_idempotency_returns_none_for_missing(db_session):
    result = await ensure_idempotency(db_session, "nonexistent-key")
    assert result is None


@pytest.mark.asyncio
async def test_ensure_idempotency_returns_existing(db_session, fake_client_id):
    key = "idem-check-001"
    tx = await credit_manual(db_session, fake_client_id, Decimal("75.0000"), idempotency_key=key)
    await db_session.commit()
    found = await ensure_idempotency(db_session, key)
    assert found is not None
    assert found.id == tx.id


@pytest.mark.asyncio
async def test_empty_idempotency_key_returns_none(db_session):
    result = await ensure_idempotency(db_session, "")
    assert result is None


@pytest.mark.asyncio
async def test_none_idempotency_key_allows_multiple_credits(db_session, fake_client_id):
    tx1 = await credit_manual(db_session, fake_client_id, Decimal("30.0000"), idempotency_key=None)
    await db_session.commit()
    tx2 = await credit_manual(db_session, fake_client_id, Decimal("20.0000"), idempotency_key=None)
    await db_session.commit()
    assert tx1.id != tx2.id
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 50.0
