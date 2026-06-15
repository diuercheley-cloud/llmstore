import httpx
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.session import get_db_session, get_redis
from app.main import app
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

settings = get_settings()


@pytest_asyncio.fixture
async def async_client(fake_redis):
    # Setup isolated SQLite for this test
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_status_security(async_client: AsyncClient):
    # Should fail without token
    response = await async_client.get("/admin/status")
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_admin_status_with_token(async_client: AsyncClient):
    # Should succeed with valid admin token
    headers = {"X-Admin-Token": settings.admin_token}
    response = await async_client.get("/admin/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "queues" in data
    assert "inference" in data


@pytest.mark.asyncio
async def test_admin_health_deep_compatibility(async_client: AsyncClient):
    # Should succeed with valid admin token (deprecated endpoint)
    headers = {"X-Admin-Token": settings.admin_token}
    response = await async_client.get("/admin/health/deep", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
