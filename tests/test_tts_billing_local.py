import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

from app.main import app
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.billing_plan import BillingPlan
from app.core.security import hash_secret, short_prefix
from app.models.api_key import ApiKey
from app.services.billing import list_client_billing_snapshots
from app.services.tts_usage import record_tts_event

@pytest_asyncio.fixture
async def tts_test_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac, testing_session_local
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.fixture
async def tts_client_simple(tts_test_env):
    ac, sessionmaker = tts_test_env
    async with sessionmaker() as session:
        plan = BillingPlan(
            code="tts_plan", name="TTS Plan", rate_limit_per_minute=10,
            daily_token_quota=1000, weekly_token_quota=5000, monthly_token_quota=10000,
            max_output_tokens=100, tts_enabled=True, tts_chars_per_request=100,
            tts_chars_per_day=500, tts_chars_per_month=2000
        )
        session.add(plan)
        await session.flush()
        client = Client(name="TTS Test Client", billing_plan_id=plan.id)
        session.add(client)
        await session.commit()
        return client, sessionmaker

@pytest.mark.asyncio
async def test_tts_in_billing_snapshot(tts_client_simple):
    client, sessionmaker = tts_client_simple
    
    async with sessionmaker() as session:
        # Record some usage
        await record_tts_event(session, client.id, 123, audio_size_bytes=456)
        await session.commit()
        
        snapshots = await list_client_billing_snapshots(session, client_id=client.id)
    
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    
    assert snapshot["daily_used_tts_chars"] == 123
    assert snapshot["monthly_used_tts_chars"] == 123
    assert snapshot["invoice_preview"]["tts_chars_used"] == 123
    assert "tts_chars_included" in snapshot["invoice_preview"]
