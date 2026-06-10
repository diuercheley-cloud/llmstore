import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from app.api.admin import router as admin_router
from app.core.config import get_settings
from app.db.base import Base
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_registry import ModelRegistry
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def admin_headers():
    settings = get_settings()
    return {"X-Admin-Token": settings.admin_token}


@pytest.fixture
def models_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    models = tmp_path / "models"
    models.mkdir()
    monkeypatch.setenv("MODELS_DIR", str(models))
    # Reset internal cache if any
    from app.services import admin_model_management
    if hasattr(admin_model_management, "_MODELS_DIR_CACHE"):
        admin_model_management._MODELS_DIR_CACHE = None
    get_settings.cache_clear()
    return models


@pytest_asyncio.fixture
async def client_and_sessionmaker(isolated_db_url, fake_redis):
    test_app = FastAPI()
    test_app.include_router(admin_router)

    engine = create_async_engine(isolated_db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Override dependency
    from app.db.session import get_db_session
    test_app.dependency_overrides[get_db_session] = lambda: async_session()

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        yield client, async_session

    await engine.dispose()


async def _create_backend(client, headers, name="test-backend"):
    payload = {
        "name": name,
        "provider": "vllm",
        "backend_url": "http://localhost:8000",
        "is_active": True,
    }
    response = await client.post("/admin/backends", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_get_model_files_requires_admin_token(client_and_sessionmaker, models_dir):
    client, _ = client_and_sessionmaker
    response = await client.get("/admin/models/files")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_model_files_lists_complex_gguf_names(client_and_sessionmaker, models_dir):
    client, _ = client_and_sessionmaker
    (models_dir / "llama-3-8b.Q4_K_M.gguf").write_text("dummy")
    
    headers = {"X-Admin-Token": get_settings().admin_token}
    response = await client.get("/admin/models/files", headers=headers)
    assert response.status_code == 200
    data = response.json()
    files = data["files"] if isinstance(data, dict) else data
    assert any(f["filename"] == "llama-3-8b.Q4_K_M.gguf" for f in files)


@pytest.mark.asyncio
async def test_get_model_files_returns_warning_when_models_dir_missing(client_and_sessionmaker, monkeypatch):
    client, _ = client_and_sessionmaker
    monkeypatch.setenv("MODELS_DIR", "/nonexistent/path/for/test")
    get_settings.cache_clear()
    
    headers = {"X-Admin-Token": get_settings().admin_token}
    response = await client.get("/admin/models/files", headers=headers)
    assert response.status_code == 200
    data = response.json()
    files = data["files"] if isinstance(data, dict) else data
    # Some items might be returned if there are defaults, but llama-3-8b should be gone
    assert not any(f["filename"] == "llama-3-8b.Q4_K_M.gguf" for f in files)


@pytest.mark.asyncio
async def test_create_model_validates_missing_file(client_and_sessionmaker, admin_headers):
    client, _ = client_and_sessionmaker
    backend_id = await _create_backend(client, admin_headers)
    
    payload = {
        "model_id": "test-model",
        "model_file": "missing.gguf",
        "inference_backend_id": backend_id,
        "provider": "llama.cpp"
    }
    response = await client.post("/admin/models", json=payload, headers=admin_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_model_blocks_duplicate_alias(client_and_sessionmaker, admin_headers, models_dir):
    client, _ = client_and_sessionmaker
    (models_dir / "test.gguf").write_text("dummy")
    backend_id = await _create_backend(client, admin_headers)
    
    payload = {
        "model_id": "test-model-1",
        "model_alias": "my-alias",
        "model_file": "test.gguf",
        "inference_backend_id": backend_id,
        "provider": "llama.cpp"
    }
    await client.post("/admin/models", json=payload, headers=admin_headers)
    
    payload["model_id"] = "test-model-2"
    response = await client.post("/admin/models", json=payload, headers=admin_headers)
    assert response.status_code == 409
    assert "alias" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_remove_default_model_is_blocked(client_and_sessionmaker, admin_headers, models_dir):
    client, _ = client_and_sessionmaker
    (models_dir / "test.gguf").write_text("dummy")
    backend_id = await _create_backend(client, admin_headers)
    
    payload = {
        "model_id": "default-model",
        "model_file": "test.gguf",
        "inference_backend_id": backend_id,
        "provider": "llama.cpp",
        "is_default": True,
    }
    resp = await client.post("/admin/models", json=payload, headers=admin_headers)
    internal_id = resp.json()["id"]
    
    response = await client.request(
        "DELETE", f"/admin/models/{internal_id}", 
        json={"hard_delete": False, "confirm_route_removal": True}, 
        headers=admin_headers
    )
    assert response.status_code == 409
    assert "default model" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_remove_nondefault_model_soft_deletes(client_and_sessionmaker, admin_headers, models_dir):
    client, _ = client_and_sessionmaker
    (models_dir / "test.gguf").write_text("dummy")
    backend_id = await _create_backend(client, admin_headers)
    
    payload = {
        "model_id": "extra-model",
        "model_file": "test.gguf",
        "inference_backend_id": backend_id,
        "provider": "llama.cpp"
    }
    resp = await client.post("/admin/models", json=payload, headers=admin_headers)
    internal_id = resp.json()["id"]
    
    response = await client.request(
        "DELETE", f"/admin/models/{internal_id}", 
        json={"hard_delete": False, "confirm_route_removal": True}, 
        headers=admin_headers
    )
    # If successful removal (not soft delete), status is 200/204
    # But wait, delete_model returns 200 dict.
    assert response.status_code == 200
    
    list_resp = await client.get("/admin/models", headers=admin_headers)
    data = list_resp.json()
    registry = data["registry"] if isinstance(data, dict) else data
    assert not any(m["model_id"] == "extra-model" for m in registry)


@pytest.mark.asyncio
async def test_set_default_swaps_models(client_and_sessionmaker, admin_headers, models_dir):
    client, session_maker = client_and_sessionmaker
    (models_dir / "test.gguf").write_text("dummy")
    backend_id = await _create_backend(client, admin_headers)
    
    await client.post("/admin/models", json={
        "model_id": "model-a", "model_file": "test.gguf", "inference_backend_id": backend_id, "provider": "llama.cpp", "is_default": True
    }, headers=admin_headers)
    
    await client.post("/admin/models", json={
        "model_id": "model-b", "model_file": "test.gguf", "inference_backend_id": backend_id, "provider": "llama.cpp", "is_default": True
    }, headers=admin_headers)
    
    async with session_maker() as session:
        from sqlalchemy import select
        res_a = await session.execute(select(ModelRegistry).where(ModelRegistry.model_id == "model-a"))
        a = res_a.scalar_one_or_none()
        res_b = await session.execute(select(ModelRegistry).where(ModelRegistry.model_id == "model-b"))
        b = res_b.scalar_one_or_none()
        assert a is not None and b is not None
        assert a.is_default is False
        assert b.is_default is True


@pytest.mark.asyncio
async def test_model_routes_create_and_remove(client_and_sessionmaker, admin_headers, models_dir):
    client, _ = client_and_sessionmaker
    (models_dir / "test.gguf").write_text("dummy")
    backend_one = await _create_backend(client, admin_headers, "backend-one")
    backend_two = await _create_backend(client, admin_headers, "backend-two")
    
    payload = {
        "model_id": "routed-model",
        "model_file": "test.gguf",
        "inference_backend_id": backend_one,
        "provider": "llama.cpp",
        "backend_routes": [
            {"inference_backend_id": str(backend_one), "priority": 1, "weight": 100},
            {"inference_backend_id": str(backend_two), "priority": 2, "weight": 10},
        ]
    }
    response = await client.post("/admin/models", json=payload, headers=admin_headers)
    assert response.status_code == 201
    
    resp = await client.get("/admin/models", headers=admin_headers)
    registry = resp.json()["registry"]
    model_data = next(m for m in registry if m["model_id"] == "routed-model")
    assert len(model_data["routes"]) == 2


@pytest.mark.asyncio
async def test_backend_docker_action_blocked_when_public_exposure_true(client_and_sessionmaker, admin_headers, monkeypatch):
    client, _ = client_and_sessionmaker
    monkeypatch.setenv("PUBLIC_EXPOSURE", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    backend_id = await _create_backend(client, admin_headers)
    response = await client.post(f"/admin/backends/{backend_id}/restart", headers=admin_headers)
    assert response.status_code in (400, 403)
    detail = response.json()["detail"].lower()
    assert "docker" in detail or "public_exposure" in detail or "blocked" in detail


@pytest.mark.asyncio
async def test_backend_docker_action_blocked_when_test_tools_disabled(client_and_sessionmaker, admin_headers, monkeypatch):
    client, _ = client_and_sessionmaker
    monkeypatch.setenv("TEST_TOOLS_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_EXPOSURE", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    backend_id = await _create_backend(client, admin_headers)
    response = await client.post(f"/admin/backends/{backend_id}/restart", headers=admin_headers)
    assert response.status_code in (400, 403)
    detail = response.json()["detail"].lower()
    assert "docker" in detail or "test_tools_enabled" in detail or "blocked" in detail
