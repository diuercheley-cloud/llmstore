from unittest.mock import patch

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.services.tts_usage import record_tts_event
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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

@pytest_asyncio.fixture
async def tts_setup(tts_test_env):
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
        await session.flush()
        await session.commit()
        return {"ac": ac, "sessionmaker": sessionmaker, "client": client}

@pytest.mark.asyncio
@patch("app.services.auth.get_admin_role")
async def test_admin_usage_summary_includes_tts(mock_get_role, tts_setup):
    from app.services.auth import AdminRole
    mock_get_role.return_value = AdminRole.SUPER
    
    ac = tts_setup["ac"]
    client = tts_setup["client"]
    sessionmaker = tts_setup["sessionmaker"]
    
    async with sessionmaker() as session:
        await record_tts_event(session, client.id, 150)
        await session.commit()
    
    response = await ac.get("/admin/usage/summary", headers={"X-Admin-Token": "test-admin-token"})
    assert response.status_code == 200
    data = response.json()
    assert "tts" in data
    assert data["tts"]["total_chars_month"] >= 150

@pytest.mark.asyncio
@patch("app.services.auth.get_admin_role")
async def test_admin_client_usage_summary_includes_tts(mock_get_role, tts_setup):
    from app.services.auth import AdminRole
    mock_get_role.return_value = AdminRole.SUPER
    
    ac = tts_setup["ac"]
    client = tts_setup["client"]
    sessionmaker = tts_setup["sessionmaker"]
    
    async with sessionmaker() as session:
        await record_tts_event(session, client.id, 200)
        await session.commit()
    
    response = await ac.get(f"/admin/usage/{client.id}/summary", headers={"X-Admin-Token": "test-admin-token"})
    assert response.status_code == 200
    data = response.json()
    assert "tts" in data
    assert data["month"]["tts_chars_used"] == 200
