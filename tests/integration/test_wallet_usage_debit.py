from decimal import Decimal

import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.billing.wallet_service import (
    InsufficientBalance,
    credit_manual,
    debit_usage,
    get_balance,
    release_reservation,
    reserve_amount,
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
async def test_debit_after_credit(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("100.0000"))
    await debit_usage(
        db_session,
        fake_client_id,
        Decimal("40.0000"),
        reference_type="chat",
        reference_id="req-001",
    )
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 60.0


@pytest.mark.asyncio
async def test_multiple_debits(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("100.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("25.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("25.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("25.0000"))
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 25.0


@pytest.mark.asyncio
async def test_exact_balance_debit(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("50.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("50.0000"))
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 0.0


@pytest.mark.asyncio
async def test_zero_debit_raises(db_session, fake_client_id):
    with pytest.raises(ValueError):
        await debit_usage(db_session, fake_client_id, Decimal("0"))


@pytest.mark.asyncio
async def test_negative_debit_raises(db_session, fake_client_id):
    with pytest.raises(ValueError):
        await debit_usage(db_session, fake_client_id, Decimal("-10.0000"))


@pytest.mark.asyncio
async def test_block_cloud_usage_when_insufficient(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("5.0000"))
    with pytest.raises(InsufficientBalance):
        await debit_usage(db_session, fake_client_id, Decimal("10.0000"))


@pytest.mark.asyncio
async def test_debit_respects_reserved_balance(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("100.0000"))
    await reserve_amount(db_session, fake_client_id, Decimal("80.0000"))
    with pytest.raises(InsufficientBalance):
        await debit_usage(db_session, fake_client_id, Decimal("50.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("20.0000"))
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 80.0


@pytest.mark.asyncio
async def test_release_reservation_frees_balance(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("100.0000"))
    await reserve_amount(db_session, fake_client_id, Decimal("60.0000"))
    await release_reservation(db_session, fake_client_id, Decimal("60.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("100.0000"))
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 0.0
