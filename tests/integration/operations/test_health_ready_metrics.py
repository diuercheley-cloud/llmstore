from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from app.db.session import get_db_session, get_redis
from app.main import app
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


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
        await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        await conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('test_version')")
        )

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
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["process"] == "alive"


@pytest.mark.asyncio
async def test_ready_endpoint_all_ok(async_client: AsyncClient):
    # Force settings with opt-in components enabled
    with patch("app.api.system.get_settings") as mock_settings:
        mock_config = MagicMock()
        mock_config.attestation_mode = "disabled"
        mock_config.rag_enabled = True
        mock_config.tts_enabled = True
        mock_config.lmstudio_enabled = True
        # Explicitly disable agent runtime and set appliance mode to avoid coherence blockers
        mock_config.agent_runtime_enabled = False
        mock_config.deployment_mode = "appliance"
        mock_config.agent_saas_connectors_enabled = False
        mock_config.agent_multi_agent_enabled = False
        mock_config.agent_stateful_workflows_enabled = False
        mock_config.agent_executor_mock_mode = False

        mock_settings.return_value = mock_config

        response = await async_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["postgres"] == "ok"
        assert data["dependencies"]["redis"] == "ok"
        assert data["dependencies"]["migrations"] == "ok"
        assert data["dependencies"]["rag"] == "ok"
        assert data["dependencies"]["tts"] == "ok"
        assert data["dependencies"]["lmstudio"] == "ok"


@pytest.mark.asyncio
async def test_ready_endpoint_degraded_when_opt_in_disabled(async_client: AsyncClient):
    # Force settings with some opt-in components disabled
    with patch("app.api.system.get_settings") as mock_settings:
        mock_config = MagicMock()
        mock_config.attestation_mode = "disabled"
        mock_config.rag_enabled = False
        mock_config.tts_enabled = False
        mock_config.lmstudio_enabled = False
        # Explicitly disable agent runtime and set appliance mode to avoid coherence blockers
        mock_config.agent_runtime_enabled = False
        mock_config.deployment_mode = "appliance"
        mock_config.agent_saas_connectors_enabled = False
        mock_config.agent_multi_agent_enabled = False
        mock_config.agent_stateful_workflows_enabled = False
        mock_config.agent_executor_mock_mode = False

        mock_settings.return_value = mock_config

        response = await async_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["postgres"] == "ok"
        assert data["dependencies"]["redis"] == "ok"
        assert data["dependencies"]["migrations"] == "ok"
        assert data["dependencies"]["rag"] == "disabled"
        assert data["dependencies"]["tts"] == "disabled"
        assert data["dependencies"]["lmstudio"] == "disabled"


@pytest.mark.asyncio
async def test_ready_endpoint_not_ready_when_postgres_fails(fake_redis):
    # Setup database that fails immediately
    async def failing_get_db():
        # Mock session that raises exception on execute
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database is down")
        yield mock_session

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db_session] = failing_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["postgres"] == "error"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_metrics_endpoint_enabled(async_client: AsyncClient):
    with patch("app.api.system.get_settings") as mock_settings:
        mock_config = MagicMock()
        mock_config.observability_enabled = True
        mock_settings.return_value = mock_config

        response = await async_client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_metrics_endpoint_disabled(async_client: AsyncClient):
    with patch("app.api.system.get_settings") as mock_settings:
        mock_config = MagicMock()
        mock_config.observability_enabled = False
        mock_settings.return_value = mock_config

        response = await async_client.get("/metrics")
        assert response.status_code == 503
        assert response.text == "metrics unavailable"
