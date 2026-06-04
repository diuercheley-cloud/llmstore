import httpx
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.session import get_db_session, get_redis
from app.main import app
from app.services.auth import require_admin
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
        # Create alembic_version table manually for /ready check
        from sqlalchemy import text
        await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('test_version')"))

    TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[require_admin] = lambda: None

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["process"] == "alive"

@pytest.mark.asyncio
async def test_ready_endpoint(async_client: AsyncClient):
    # In test environment, dependencies should be ready
    response = await async_client.get("/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "dependencies" in data

@pytest.mark.asyncio
async def test_status_endpoint(async_client: AsyncClient):
    response = await async_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "api" in data["components"]
    
    # Ensure no secrets leaked (basic check)
    content = response.text.lower()
    for secret_word in ["key", "token", "password", "secret"]:
        assert secret_word not in content or f'"{secret_word}"' not in content

@pytest.mark.asyncio
async def test_deep_health_admin(async_client: AsyncClient):
    response = await async_client.get("/admin/health/deep")
    assert response.status_code == 200
    data = response.json()
    assert "dependencies" in data
    assert "data_plane" in data["dependencies"]
    assert "ok" in data["dependencies"]["data_plane"]
    assert "latency_ms" in data["dependencies"]["data_plane"]


@pytest.mark.asyncio
async def test_client_portal_page_supports_api_key_bootstrap(async_client: AsyncClient):
    response = await async_client.get("/client-portal")
    assert response.status_code == 200
    # The client portal links to portal.js
    assert "portal.js" in response.text
    
    js_response = await async_client.get("/static/portal/portal.js")
    assert js_response.status_code == 200
    assert "readApiKeyFromUrl" in js_response.text
    assert "searchParams.get('api_key')" in js_response.text
    assert "window.history.replaceState" in js_response.text
