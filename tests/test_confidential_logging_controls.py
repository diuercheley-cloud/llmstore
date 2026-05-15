import pytest
import uuid
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.inference import confidential_runtime
from app.models.commercial_confidential_runtime import CommercialConfidentialRuntimeProfile, CommercialConfidentialInferenceSession

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base

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
async def test_enforce_no_plaintext_logging_blocked(session: AsyncSession):
    profile = CommercialConfidentialRuntimeProfile(
        profile_name="Secure",
        prohibit_prompt_logging=True
    )
    conf_session = CommercialConfidentialInferenceSession(id=uuid.uuid4())
    
    prompt = "What is the secret recipe?"
    expected_hash = hashlib.sha256(prompt.encode()).hexdigest()
    
    # We need to mock settings or assume they are enabled for the test
    # The service uses get_settings().commercial_confidential_prohibit_plaintext_logging
    # For now we assume default is True in tests or we'd need to mock it.
    
    result = await confidential_runtime.enforce_no_plaintext_logging(
        session, conf_session, profile, "prompt", prompt
    )
    
    assert result == expected_hash
    assert result != prompt

@pytest.mark.asyncio
async def test_enforce_no_plaintext_logging_allowed(session: AsyncSession):
    profile = CommercialConfidentialRuntimeProfile(
        profile_name="Relaxed",
        prohibit_prompt_logging=False
    )
    conf_session = CommercialConfidentialInferenceSession(id=uuid.uuid4())
    
    prompt = "Hello"
    result = await confidential_runtime.enforce_no_plaintext_logging(
        session, conf_session, profile, "prompt", prompt
    )
    
    assert result == prompt
