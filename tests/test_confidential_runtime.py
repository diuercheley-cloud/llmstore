
import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.commercial_confidential_runtime import CommercialConfidentialRuntimeProfile
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
async def test_resolve_profile_global(session: AsyncSession):
    # Create global profile
    profile = CommercialConfidentialRuntimeProfile(
        profile_name="Global Default",
        client_id=None,
        enabled=True
    )
    session.add(profile)
    await session.commit()
    
    resolved = await confidential_runtime.resolve_confidential_profile(session, "any-client")
    assert resolved.profile_name == "Global Default"

@pytest.mark.asyncio
async def test_resolve_profile_client_specific(session: AsyncSession):
    # Create global and client profiles
    session.add(CommercialConfidentialRuntimeProfile(profile_name="Global", client_id=None))
    session.add(CommercialConfidentialRuntimeProfile(profile_name="ClientX", client_id="client-x"))
    await session.commit()
    
    resolved = await confidential_runtime.resolve_confidential_profile(session, "client-x")
    assert resolved.profile_name == "ClientX"

@pytest.mark.asyncio
async def test_create_session(session: AsyncSession):
    profile = CommercialConfidentialRuntimeProfile(profile_name="Test")
    session.add(profile)
    await session.commit()
    
    conf_session = await confidential_runtime.create_confidential_session(
        session, "client1", "req123", profile
    )
    assert conf_session.request_id == "req123"
    assert conf_session.profile_id == profile.id
