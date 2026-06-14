import pytest
from uuid import uuid4


@pytest.mark.asyncio
async def test_lifecycle_reconcile_all_endpoint(admin_client, admin_token_headers):
    from app.db.base import Base
    from app.models.core.inference_backend import InferenceBackend
    from app.services.runtime_dependencies import get_db_session
    from app.api.deps import get_inference_proxy
    from app.main import app
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(InferenceBackend(
            name="test-a", provider="llama.cpp",
            backend_url="http://localhost:8080", is_active=True,
        ))
        session.add(InferenceBackend(
            name="test-b", provider="vllm",
            backend_url="http://localhost:8000", is_active=False,
        ))
        await session.commit()

    async def override_db():
        async with session_factory() as s:
            yield s

    old_db = app.dependency_overrides.get(get_db_session)
    old_proxy = app.dependency_overrides.get(get_inference_proxy)
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_inference_proxy] = lambda: None

    try:
        response = await admin_client.post(
            "/admin/backends/lifecycle/reconcile-all",
            headers=admin_token_headers,
        )
    finally:
        if old_db:
            app.dependency_overrides[get_db_session] = old_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if old_proxy:
            app.dependency_overrides[get_inference_proxy] = old_proxy
        else:
            app.dependency_overrides.pop(get_inference_proxy, None)
        await engine.dispose()

    assert response.status_code == 200, f"expected 200 got {response.status_code}: {response.text}"
    payload = response.json()
    assert payload["reconciled"] == 2


@pytest.mark.asyncio
async def test_lifecycle_drift_history_empty(admin_client, admin_token_headers):
    response = await admin_client.get(
        "/admin/backends/lifecycle/drift-history",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "drifts" in payload
    assert payload["drifts"] == []


@pytest.mark.asyncio
async def test_lifecycle_observed_not_found(admin_client, admin_token_headers):
    response = await admin_client.get(
        f"/admin/backends/{uuid4()}/lifecycle/observed",
        headers=admin_token_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_lifecycle_reconcile_not_found(admin_client, admin_token_headers):
    response = await admin_client.post(
        f"/admin/backends/{uuid4()}/lifecycle/reconcile",
        headers=admin_token_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_backend_not_found(admin_client, admin_token_headers):
    response = await admin_client.post(
        f"/admin/backends/{uuid4()}/start",
        headers=admin_token_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stop_backend_not_found(admin_client, admin_token_headers):
    response = await admin_client.post(
        f"/admin/backends/{uuid4()}/stop",
        headers=admin_token_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_restart_backend_not_found(admin_client, admin_token_headers):
    response = await admin_client.post(
        f"/admin/backends/{uuid4()}/restart",
        headers=admin_token_headers,
    )
    assert response.status_code == 404
