import pytest
import pytest_asyncio
from app.db.session import get_redis
from app.main import app
from httpx import AsyncClient


@pytest_asyncio.fixture
async def fastapi_app(fake_redis):
    # Override dependencies for the global app instance during tests
    app.dependency_overrides[get_redis] = lambda: fake_redis
    yield app
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rag_routes_exist():
    # We check if routes are registered in the app
    routes = [route.path for route in app.routes]

    assert "/v1/rag/files" in routes
    assert "/v1/rag/query" in routes
    assert "/admin/tests/rag/status" in routes
    assert "/client-portal" in routes


@pytest.mark.asyncio
async def test_rag_upload_returns_401_no_auth(async_client: AsyncClient):
    # Use the real app instance if possible or the one from conftest
    # async_client already uses app from main via conftest if configured
    response = await async_client.post("/v1/rag/files")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rag_query_returns_401_no_auth(async_client: AsyncClient):
    response = await async_client.post("/v1/rag/query", json={"question": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_rag_status_returns_401_no_auth(async_client: AsyncClient):
    response = await async_client.get("/admin/tests/rag/status")
    assert response.status_code == 401
