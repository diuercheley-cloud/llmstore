
import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.commercial_cryptographic_receipts import CommercialInferenceReceipt
from app.services.inference import public_attestation_gateway
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_local() as s:
        yield s
    await engine.dispose()

@pytest.mark.asyncio
async def test_log_request(session: AsyncSession):
    req = await public_attestation_gateway.log_attestation_request(
        session, "hash123", source_ip="1.2.3.4", user_agent="Pytest"
    )
    assert req.request_hash == "hash123"
    assert req.source_ip == "1.2.x.x" # Masked
    assert req.status == "received"

@pytest.mark.asyncio
async def test_verify_receipt_not_found(session: AsyncSession):
    result = await public_attestation_gateway.verify_public_receipt(session, "nonexistent")
    assert result["status"] == "invalid"
    assert "not found" in result["message"]

@pytest.mark.asyncio
async def test_verify_receipt_valid(session: AsyncSession):
    # Create a real receipt
    receipt = CommercialInferenceReceipt(
        receipt_hash="valid_hash",
        prompt_hash="p",
        response_hash="r",
        client_id="client1",
        verification_status="valid"
    )
    session.add(receipt)
    await session.commit()
    
    result = await public_attestation_gateway.verify_public_receipt(session, "valid_hash")
    assert result["status"] == "valid"
    assert result["verification_status"] == "valid"

@pytest.mark.asyncio
async def test_sanitize_result():
    data = {
        "id": "123",
        "internal_id": "secret",
        "quorum_status": "met",
        "signatures": [{"witness_id": "W1", "raw_secret": "XXX"}]
    }
    sanitized = public_attestation_gateway.sanitize_public_result(data)
    assert "internal_id" not in sanitized
    assert "signatures" in sanitized
    assert "raw_secret" not in sanitized["signatures"][0]
