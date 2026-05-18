import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import uuid
from sqlalchemy import select
from app.main import app
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

@pytest_asyncio.fixture
async def client(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with TestingSessionLocal() as session:
            yield session

    def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = override_get_redis
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
        
    app.dependency_overrides.clear()

@pytest.fixture
def admin_headers():
    return {"X-Admin-Token": get_settings().admin_token}

@pytest.fixture
def read_headers():
    return {"X-Admin-Token": get_settings().admin_read_token or get_settings().admin_token}

@pytest.mark.asyncio
async def test_admin_tests_page_html(client):
    response = await client.get("/admin-tests")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Admin Tests - LLM Inference Stack" in response.text

@pytest.mark.asyncio
async def test_admin_tests_system_resources(client, admin_headers):
    response = await client.get("/admin/tests/system/resources", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "memory" in data
    assert "gpu" in data
    assert "available" in data["gpu"]

@pytest.mark.asyncio
async def test_admin_tests_user_not_found(client, admin_headers):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/admin/tests/users/{fake_id}", headers=admin_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_admin_tests_set_quota_negative(client, admin_headers):
    fake_id = str(uuid.uuid4())
    response = await client.post(f"/admin/tests/users/{fake_id}/quota/set", json={"daily_quota": -1}, headers=admin_headers)
    assert response.status_code in [400, 404]

@pytest.mark.asyncio
async def test_chat_completions_401_no_token(client):
    response = await client.post("/v1/chat/completions", json={"model": "gemma", "messages": []})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_audit_logs_unauthorized(client):
    response = await client.get("/admin/tests/audit")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_audit_logs_authorized(client, admin_headers):
    response = await client.get("/admin/tests/audit", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_auth_whoami(client, admin_headers):
    response = await client.get("/admin/tests/auth/whoami", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "role" in data

@pytest.mark.asyncio
async def test_openrouter_backend_status_returns_backend_url(client, admin_headers):
    async for session in app.dependency_overrides[get_db_session]():
        backend = InferenceBackend(
            name="openrouter-test-backend",
            provider="openrouter",
            backend_url="https://openrouter.ai/api/v1",
            healthcheck_path="/health",
            is_active=True,
        )
        session.add(backend)
        await session.commit()
        await session.refresh(backend)

    response = await client.get("/admin/tests/openrouter/backend", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["name"] == "openrouter-test-backend"
    assert data["base_url"] == "https://openrouter.ai/api/v1"


@pytest.mark.asyncio
async def test_openrouter_configure_reassigns_alias_when_model_id_already_exists(client, admin_headers, monkeypatch):
    async def fake_fetch_metadata(model_id: str):
        return {}

    monkeypatch.setattr("app.api.admin_tests._fetch_openrouter_model_metadata", fake_fetch_metadata)

    async for session in app.dependency_overrides[get_db_session]():
        backend = InferenceBackend(
            name="openrouter-test-backend",
            provider="openrouter",
            backend_url="https://openrouter.ai/api/v1",
            healthcheck_path="/health",
            is_active=True,
        )
        existing_target = ModelRegistry(
            model_id="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            model_alias="nemotron-reasoning",
            provider="openrouter",
            model_file="",
            context_length=131072,
            is_active=True,
            is_default=False,
            status="configured",
            prompt_template="qwen",
        )
        existing_alias = ModelRegistry(
            model_id="nvidia/nemotron-3-nano-30b-a3b:free",
            model_alias="openrouter-test",
            provider="openrouter",
            model_file="",
            context_length=131072,
            is_active=True,
            is_default=False,
            status="configured",
            prompt_template="qwen",
        )
        session.add_all([backend, existing_target, existing_alias])
        await session.commit()
        await session.refresh(backend)
        await session.refresh(existing_target)
        await session.refresh(existing_alias)

        session.add(
            ModelBackendRoute(
                model_registry_id=existing_alias.id,
                inference_backend_id=backend.id,
                priority=1,
                weight=100,
                state="healthy",
            )
        )
        await session.commit()

    response = await client.post(
        "/admin/tests/openrouter/configure",
        headers=admin_headers,
        json={
            "model_id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            "model_alias": "openrouter-test",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    async for session in app.dependency_overrides[get_db_session]():
        target = await session.get(ModelRegistry, existing_target.id)
        stale_alias = await session.get(ModelRegistry, existing_alias.id)

        assert target is not None
        assert target.model_alias == "openrouter-test"
        assert target.inference_backend_id == backend.id

        assert stale_alias is not None
        assert stale_alias.model_alias is None

        route = (
            await session.execute(
                select(ModelBackendRoute).where(
                    ModelBackendRoute.model_registry_id == target.id,
                    ModelBackendRoute.inference_backend_id == backend.id,
                )
            )
        )
        assert route.scalars().first() is not None
