import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.commercial.commercial_confidential_runtime import (
    CommercialConfidentialInferenceSession,
    CommercialConfidentialRuntimeProfile,
)
from app.services.inference import confidential_runtime
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
async def test_validate_encrypted_input_missing(session: AsyncSession):
    profile = CommercialConfidentialRuntimeProfile(
        profile_name="High Security", require_encrypted_input=True
    )
    conf_session = CommercialConfidentialInferenceSession()

    payload = {"prompt": "Plaintext"}
    is_valid, msg = await confidential_runtime.validate_confidential_request(
        session, conf_session, profile, payload
    )

    assert not is_valid
    assert "Encrypted input required" in msg


@pytest.mark.asyncio
async def test_validate_encrypted_input_present(session: AsyncSession):
    profile = CommercialConfidentialRuntimeProfile(
        profile_name="High Security", require_encrypted_input=True
    )
    conf_session = CommercialConfidentialInferenceSession()

    payload = {"encrypted_input": "0xABCDEF"}
    is_valid, msg = await confidential_runtime.validate_confidential_request(
        session, conf_session, profile, payload
    )

    assert is_valid


@pytest.mark.asyncio
async def test_apply_retention_policy(session: AsyncSession):
    profile = CommercialConfidentialRuntimeProfile(
        profile_name="No Retention", max_retention_seconds=0
    )
    conf_session = CommercialConfidentialInferenceSession()
    session.add(conf_session)
    await session.commit()

    await confidential_runtime.apply_retention_policy(session, conf_session, profile)

    assert conf_session.retention_policy_applied == True
    assert conf_session.completed_at is not None
