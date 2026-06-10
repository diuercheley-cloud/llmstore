from decimal import Decimal

import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.billing.wallet_service import (
    InsufficientBalance,
    adjustment,
    credit_manual,
    debit_usage,
    get_balance,
    get_or_create_wallet,
    refund,
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
async def test_get_or_create_wallet_creates_new(db_session, fake_client_id):
    wallet = await get_or_create_wallet(db_session, fake_client_id)
    assert wallet is not None
    assert wallet.client_id == fake_client_id
    assert wallet.currency == "BRL"
    assert wallet.balance_brl == Decimal("0.0000")
    assert wallet.status == "active"


@pytest.mark.asyncio
async def test_get_or_create_wallet_returns_existing(db_session, fake_client_id):
    w1 = await get_or_create_wallet(db_session, fake_client_id)
    w2 = await get_or_create_wallet(db_session, fake_client_id)
    assert w1.id == w2.id


@pytest.mark.asyncio
async def test_credit_manual_increases_balance(db_session, fake_client_id):
    tx = await credit_manual(db_session, fake_client_id, Decimal("100.0000"), reason="test credit")
    await db_session.commit()
    assert tx.amount_brl == Decimal("100.0000")
    assert tx.type == "manual_credit"
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 100.0


@pytest.mark.asyncio
async def test_credit_manual_positive_only(db_session, fake_client_id):
    with pytest.raises(ValueError):
        await credit_manual(db_session, fake_client_id, Decimal("0"))


@pytest.mark.asyncio
async def test_debit_usage_reduces_balance(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("50.0000"))
    tx = await debit_usage(db_session, fake_client_id, Decimal("30.0000"), reference_type="chat", reference_id="req-001")
    await db_session.commit()
    assert tx.amount_brl == Decimal("-30.0000")
    assert tx.type == "usage_debit"
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 20.0


@pytest.mark.asyncio
async def test_debit_usage_insufficient_balance(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("10.0000"))
    with pytest.raises(InsufficientBalance):
        await debit_usage(db_session, fake_client_id, Decimal("20.0000"))


@pytest.mark.asyncio
async def test_reserve_and_release(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("100.0000"))
    await reserve_amount(db_session, fake_client_id, Decimal("30.0000"))
    balance = await get_balance(db_session, fake_client_id)
    assert balance["reserved_brl"] == 30.0
    assert balance["available_brl"] == 70.0
    await release_reservation(db_session, fake_client_id, Decimal("30.0000"))
    balance = await get_balance(db_session, fake_client_id)
    assert balance["reserved_brl"] == 0.0
    assert balance["available_brl"] == 100.0


@pytest.mark.asyncio
async def test_reservation_insufficient_balance(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("10.0000"))
    with pytest.raises(InsufficientBalance):
        await reserve_amount(db_session, fake_client_id, Decimal("20.0000"))


@pytest.mark.asyncio
async def test_refund_increases_balance(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("50.0000"))
    await debit_usage(db_session, fake_client_id, Decimal("20.0000"))
    tx = await refund(db_session, fake_client_id, Decimal("20.0000"), reason="refund test")
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 50.0
    assert tx.type == "refund"


@pytest.mark.asyncio
async def test_adjustment_credit(db_session, fake_client_id):
    tx = await adjustment(db_session, fake_client_id, Decimal("200.0000"), reason="promotional credit")
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 200.0
    assert tx.type == "adjustment"


@pytest.mark.asyncio
async def test_adjustment_debit(db_session, fake_client_id):
    await credit_manual(db_session, fake_client_id, Decimal("100.0000"))
    tx = await adjustment(db_session, fake_client_id, Decimal("-50.0000"), reason="chargeback")
    await db_session.commit()
    balance = await get_balance(db_session, fake_client_id)
    assert balance["balance_brl"] == 50.0


@pytest.mark.asyncio
async def test_adjustment_negative_not_allowed(db_session, fake_client_id):
    with pytest.raises(InsufficientBalance):
        await adjustment(db_session, fake_client_id, Decimal("-50.0000"))


@pytest.mark.asyncio
async def test_get_balance_returns_correct_structure(db_session, fake_client_id):
    balance = await get_balance(db_session, fake_client_id)
    assert "wallet_id" in balance
    assert "client_id" in balance
    assert balance["currency"] == "BRL"
    assert balance["balance_brl"] == 0.0
    assert balance["reserved_brl"] == 0.0
    assert balance["available_brl"] == 0.0
    assert balance["status"] == "active"
