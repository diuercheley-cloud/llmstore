import os

# Register all models in Base.metadata BEFORE importing app
import httpx
import pytest
import pytest_asyncio
from app.api.dependencies import get_db
from app.api.deps import (
    get_backend_slot_manager,
    get_circuit_breaker,
    get_inference_proxy,
    get_queue_manager,
)
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app as fastapi_app
from app.services.admin_rbac import ensure_admin_rbac_seed
from app.services.inference_proxy import InferenceProxy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from data_plane_mock.main import app as mock_data_plane_app
except ImportError:
    mock_data_plane_app = None
    pytest.skip(
        "data_plane_mock module not available, skipping e2e tests that depend on it.",
        allow_module_level=True,
    )


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def e2e_client(isolated_db_url, fake_redis, monkeypatch):
    """
    Provides an AsyncClient for E2E tests with an isolated database and mock data plane.
    """
    monkeypatch.setenv("RBAC_ADMIN_ENABLED", "true")
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("EMBEDDINGS_ENABLED", "true")
    monkeypatch.setenv("EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_ASYNC_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("MODEL_HOT_SWAP_ENABLED", "true")
    monkeypatch.setenv("PKI_ENABLED", "true")
    monkeypatch.setenv("REDIS_URL", "redis://test.invalid:6379")

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    # Ensure model_runtime_instances table is registered before create_all

    # Verify table registration
    if "model_runtime_instances" not in Base.metadata.tables:
        raise RuntimeError(
            f"Table not registered. Available: {sorted(Base.metadata.tables.keys())}"
        )

    # Mock Data Plane redirection
    mock_transport = httpx.ASGITransport(app=mock_data_plane_app)
    original_get_client = InferenceProxy._get_client

    def mocked_get_client(self, base_url: str):
        if "localhost:8081" in base_url or "testserver" in base_url:
            return httpx.AsyncClient(transport=mock_transport, base_url=base_url)
        return original_get_client(self, base_url)

    monkeypatch.setattr(InferenceProxy, "_get_client", mocked_get_client)

    monkeypatch.setenv("DATABASE_URL", isolated_db_url)
    get_settings.cache_clear()
    settings = get_settings()

    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Monkeypatch SessionLocal so any internal import (e.g. model_runtime_manager)
    # uses our test database
    import app.db.session as db_session_mod

    monkeypatch.setattr(db_session_mod, "SessionLocal", testing_session_local)

    # Mock BackendSlotManager to avoid SQLite "database is locked" (it uses with_for_update,
    # which is Postgres-only) and to avoid session conflicts with the test's override_get_db.
    # The QueueManager's own slot counting still provides concurrency control.
    async def mock_try_acquire(self, backend_id):
        return True

    async def mock_release(self, backend_id):
        pass

    monkeypatch.setattr(
        "app.services.backend_slot_manager.BackendSlotManager.try_acquire", mock_try_acquire
    )
    monkeypatch.setattr(
        "app.services.backend_slot_manager.BackendSlotManager.release", mock_release
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with testing_session_local() as session:
        await ensure_admin_rbac_seed(session)
        await session.commit()

    async def override_get_db():
        async with testing_session_local() as session:
            yield session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db  # for direct calls
    fastapi_app.dependency_overrides[get_db] = override_get_db  # for dependencies.py
    fastapi_app.dependency_overrides[get_redis] = lambda: fake_redis

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def admin_headers():
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")
    return {"X-Admin-Token": token}


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Clears lru_cache singletons that bind to the event loop (QueueManager,
    InferenceProxy, BackendSlotManager, CircuitBreaker).
    Without this, tests that reuse these singletons across event loops will
    crash with "bound to a different event loop".
    """
    get_queue_manager.cache_clear()
    get_inference_proxy.cache_clear()
    get_backend_slot_manager.cache_clear()
    get_circuit_breaker.cache_clear()
    yield
