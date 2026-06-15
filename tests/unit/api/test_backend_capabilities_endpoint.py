from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


class DummyProxy:
    def __init__(self) -> None:
        self.health_backend = AsyncMock(
            return_value={"ok": True, "status": "healthy", "latency_ms": 4.2}
        )
        self.list_models = AsyncMock(return_value={"data": [{"id": "chat"}, {"id": "embed"}]})


class UnavailableModelsProxy:
    def __init__(self) -> None:
        self.health_backend = AsyncMock(
            return_value={"ok": False, "status": "unhealthy", "latency_ms": 4.2}
        )
        self.list_models = AsyncMock(
            side_effect=HTTPException(status_code=503, detail="backend unavailable")
        )


@pytest.mark.asyncio
async def test_backend_capabilities_endpoint(async_client, monkeypatch):
    from app.api.deps import get_inference_proxy
    from app.db.base import Base
    from app.db.session import get_db_session
    from app.main import app
    from app.models.core.inference_backend import InferenceBackend
    from app.services.runtime_dependencies import get_db_session as get_runtime_db_session
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with session_factory() as session:
            session.add(
                InferenceBackend(
                    name="vllm-local",
                    provider="vllm",
                    backend_url="http://localhost:8000",
                    is_active=True,
                    is_default=True,
                )
            )
            await session.commit()
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_runtime_db_session] = override_get_db_session
    app.dependency_overrides[get_inference_proxy] = lambda: DummyProxy()
    try:
        response = await async_client.get("/api/backends/capabilities")
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_runtime_db_session, None)
        app.dependency_overrides.pop(get_inference_proxy, None)
        await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["streaming"] == 1
    assert payload["summary"]["tool_calling"] == 1
    assert payload["backends"][0]["provider"] == "vllm"


@pytest.mark.asyncio
async def test_backend_capabilities_endpoint_degrades_when_models_are_unavailable(
    async_client,
):
    from app.api.deps import get_inference_proxy
    from app.db.base import Base
    from app.db.session import get_db_session
    from app.main import app
    from app.models.core.inference_backend import InferenceBackend
    from app.services.runtime_dependencies import get_db_session as get_runtime_db_session
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with session_factory() as session:
            session.add(
                InferenceBackend(
                    name="offline-vllm",
                    provider="vllm",
                    backend_url="http://localhost:8000",
                    is_active=True,
                    is_default=True,
                )
            )
            await session.commit()
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_runtime_db_session] = override_get_db_session
    app.dependency_overrides[get_inference_proxy] = lambda: UnavailableModelsProxy()
    try:
        response = await async_client.get("/api/backends/capabilities")
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_runtime_db_session, None)
        app.dependency_overrides.pop(get_inference_proxy, None)
        await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 1
    assert payload["summary"]["healthy"] == 0
    assert payload["backends"][0]["benchmark"]["model_count"] == 0
    assert payload["backends"][0]["benchmark"]["model_listing_error"]["status_code"] == 503
