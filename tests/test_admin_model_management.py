import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.admin import router as admin_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.model_registry import ModelRegistry
from app.services import admin_model_management as model_mgmt


@pytest_asyncio.fixture
async def client_and_sessionmaker(isolated_db_url, fake_redis):
    test_app = FastAPI()
    test_app.include_router(admin_router)
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    test_app.dependency_overrides[get_db_session] = override_get_db_session
    test_app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as ac:
        yield ac, testing_session_local

    test_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def admin_headers():
    settings = get_settings()
    return {"X-Admin-Token": settings.admin_token}


@pytest.fixture
def models_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    directory = tmp_path / "models"
    directory.mkdir()
    monkeypatch.setattr(model_mgmt, "resolve_models_dir", lambda: directory)
    return directory


async def _create_backend(client: AsyncClient, admin_headers: dict, name: str = "backend-one") -> str:
    response = await client.post(
        "/admin/backends",
        json={
            "name": name,
            "provider": "llama.cpp",
            "backend_url": "http://backend.local",
            "healthcheck_path": "/health",
            "is_active": True,
            "is_default": False,
            "status": "configured",
            "max_parallel_requests": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_model(
    client: AsyncClient,
    admin_headers: dict,
    backend_id: str,
    *,
    model_id: str,
    alias: str,
    model_file: str,
    is_default: bool = False,
):
    return await client.post(
        "/admin/models",
        json={
            "display_name": alias.title(),
            "model_id": model_id,
            "model_alias": alias,
            "provider": "llama.cpp",
            "model_file": model_file,
            "inference_backend_id": backend_id,
            "context_length": 4096,
            "is_active": True,
            "is_default": is_default,
            "status": "configured",
            "prompt_template": "auto",
        },
        headers=admin_headers,
    )


@pytest.mark.asyncio
async def test_get_model_files_requires_admin_token(client_and_sessionmaker, models_dir, admin_headers):
    client, _ = client_and_sessionmaker
    (models_dir / "sample.gguf").write_bytes(b"gguf")

    unauthorized = await client.get("/admin/models/files")
    assert unauthorized.status_code in {401, 403}

    authorized = await client.get("/admin/models/files", headers=admin_headers)
    assert authorized.status_code == 200
    payload = authorized.json()
    assert payload["files"][0]["filename"] == "sample.gguf"


@pytest.mark.asyncio
async def test_create_model_validates_missing_file(client_and_sessionmaker, models_dir, admin_headers):
    client, _ = client_and_sessionmaker
    backend_id = await _create_backend(client, admin_headers)

    response = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/missing",
        alias="missing",
        model_file="does-not-exist.gguf",
    )
    assert response.status_code == 404
    assert "model file not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_model_blocks_duplicate_alias(client_and_sessionmaker, models_dir, admin_headers):
    client, _ = client_and_sessionmaker
    (models_dir / "one.gguf").write_bytes(b"gguf-1")
    (models_dir / "two.gguf").write_bytes(b"gguf-2")
    backend_id = await _create_backend(client, admin_headers)

    first = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/model-one",
        alias="dup-alias",
        model_file="one.gguf",
    )
    assert first.status_code == 201

    duplicate = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/model-two",
        alias="dup-alias",
        model_file="two.gguf",
    )
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


@pytest.mark.asyncio
async def test_remove_default_model_is_blocked(client_and_sessionmaker, models_dir, admin_headers):
    client, _ = client_and_sessionmaker
    (models_dir / "default.gguf").write_bytes(b"gguf-default")
    backend_id = await _create_backend(client, admin_headers)
    created = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/default-model",
        alias="default-model",
        model_file="default.gguf",
        is_default=True,
    )
    model_id = created.json()["id"]

    response = await client.request(
        "DELETE",
        f"/admin/models/{model_id}",
        json={"confirm_route_removal": True, "mode": "auto"},
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert "default model cannot be removed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_remove_nondefault_model_soft_deletes(client_and_sessionmaker, models_dir, admin_headers):
    client, session_factory = client_and_sessionmaker
    (models_dir / "soft.gguf").write_bytes(b"gguf-soft")
    backend_id = await _create_backend(client, admin_headers)
    created = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/soft-delete",
        alias="soft-delete",
        model_file="soft.gguf",
    )
    model_id = created.json()["id"]

    response = await client.request(
        "DELETE",
        f"/admin/models/{model_id}",
        json={"confirm_route_removal": True, "mode": "soft"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "soft-deleted"

    async with session_factory() as session:
        archived = await session.get(ModelRegistry, uuid.UUID(model_id))
        assert archived is not None
        assert archived.status == "soft-deleted"
        assert archived.is_active is False


@pytest.mark.asyncio
async def test_set_default_swaps_models(client_and_sessionmaker, models_dir, admin_headers):
    client, session_factory = client_and_sessionmaker
    (models_dir / "one.gguf").write_bytes(b"gguf-one")
    (models_dir / "two.gguf").write_bytes(b"gguf-two")
    backend_id = await _create_backend(client, admin_headers)
    one = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/one",
        alias="one",
        model_file="one.gguf",
        is_default=True,
    )
    two = await _create_model(
        client,
        admin_headers,
        backend_id,
        model_id="org/two",
        alias="two",
        model_file="two.gguf",
    )
    response = await client.post(f"/admin/models/{two.json()['id']}/set-default", headers=admin_headers)
    assert response.status_code == 200

    async with session_factory() as session:
        rows = (await session.execute(select(ModelRegistry).order_by(ModelRegistry.model_id.asc()))).scalars().all()
        defaults = {row.model_id: row.is_default for row in rows}
        assert defaults["org/one"] is False
        assert defaults["org/two"] is True


@pytest.mark.asyncio
async def test_model_routes_create_and_remove(client_and_sessionmaker, models_dir, admin_headers):
    client, _ = client_and_sessionmaker
    (models_dir / "routes.gguf").write_bytes(b"gguf-routes")
    backend_one = await _create_backend(client, admin_headers, "backend-one")
    backend_two = await _create_backend(client, admin_headers, "backend-two")
    model = await _create_model(
        client,
        admin_headers,
        backend_one,
        model_id="org/routes",
        alias="routes",
        model_file="routes.gguf",
    )
    model_id = model.json()["id"]

    create_route = await client.post(
        f"/admin/models/{model_id}/routes",
        json={"inference_backend_id": backend_two, "priority": 10, "weight": 50, "state": "healthy"},
        headers=admin_headers,
    )
    assert create_route.status_code == 200
    created_payload = create_route.json()
    assert len(created_payload["routes"]) == 2
    assert {route["backend_name"] for route in created_payload["routes"]} == {"backend-one", "backend-two"}

    delete_route = await client.delete(
        f"/admin/models/{model_id}/routes/{backend_two}",
        headers=admin_headers,
    )
    assert delete_route.status_code == 200
    assert delete_route.json()["status"] == "route-removed"


@pytest.mark.asyncio
async def test_backend_docker_action_blocked_when_public_exposure_true(client_and_sessionmaker, admin_headers):
    client, _ = client_and_sessionmaker
    backend_id = await _create_backend(client, admin_headers)
    settings = get_settings()
    previous_public = settings.public_exposure
    previous_tools = settings.test_tools_enabled
    settings.public_exposure = True
    settings.test_tools_enabled = True
    try:
        response = await client.post(f"/admin/backends/{backend_id}/start", headers=admin_headers)
        assert response.status_code == 403
        assert "PUBLIC_EXPOSURE=true" in response.json()["detail"]
    finally:
        settings.public_exposure = previous_public
        settings.test_tools_enabled = previous_tools


@pytest.mark.asyncio
async def test_backend_docker_action_blocked_when_test_tools_disabled(client_and_sessionmaker, admin_headers):
    client, _ = client_and_sessionmaker
    backend_id = await _create_backend(client, admin_headers)
    settings = get_settings()
    previous_public = settings.public_exposure
    previous_tools = settings.test_tools_enabled
    settings.public_exposure = False
    settings.test_tools_enabled = False
    try:
        response = await client.post(f"/admin/backends/{backend_id}/restart", headers=admin_headers)
        assert response.status_code == 403
        assert "TEST_TOOLS_ENABLED=false" in response.json()["detail"]
    finally:
        settings.public_exposure = previous_public
        settings.test_tools_enabled = previous_tools
