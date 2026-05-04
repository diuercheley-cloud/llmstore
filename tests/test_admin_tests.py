import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import uuid
from app.main import app
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session, get_redis
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
