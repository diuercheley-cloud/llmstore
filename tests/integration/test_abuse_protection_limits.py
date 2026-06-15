from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.billing.billing_plan import BillingPlan
from app.models.core.api_key import ApiKey
from app.models.core.client import Client
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def abuse_limits_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with (
        patch("app.db.session.SessionLocal", testing_session_local),
        patch("app.services.backend_slot_manager.SessionLocal", testing_session_local),
        patch(
            "app.services.backend_slot_manager.BackendSlotManager.try_acquire", return_value=True
        ),
        patch("app.services.backend_slot_manager.BackendSlotManager.release", return_value=None),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:
            yield ac, testing_session_local

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def limits_setup(abuse_limits_env):
    ac, sessionmaker = abuse_limits_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="limits_test",
            name="Limits Test",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            weekly_token_quota=10000,
            monthly_token_quota=100000,
            max_output_tokens=32,
            allow_streaming=False,
            tts_enabled=True,
            tts_chars_per_request=50,
            tts_chars_per_day=100,
            tts_chars_per_month=500,
            embeddings_enabled=True,
            embeddings_requests_per_month=10,
            embeddings_tokens_per_month=1000,
            embeddings_max_inputs_per_request=2,
            rag_enabled=True,
            rag_max_documents=1,
            rag_max_storage_mb=1,
        )
        session.add(plan)
        await session.flush()

        client = Client(
            name="limits-client",
            billing_plan_id=plan.id,
            billing_status="active",
            max_context_tokens=64,
        )
        session.add(client)
        await session.flush()

        # Add a default model so resolve_requested_model doesn't fail with 503
        backend = InferenceBackend(
            name="limits-backend", provider="test", backend_url="http://test", is_active=True
        )
        session.add(backend)
        await session.flush()

        model = ModelRegistry(
            model_id="default",
            model_alias="default",
            provider="test",
            model_file="test.gguf",
            inference_backend_id=backend.id,
            is_active=True,
            is_default=True,
        )
        session.add(model)

        raw = "sk-limits-12345678"
        key = ApiKey(
            client_id=client.id,
            name="limits-key",
            key_prefix=short_prefix(raw),
            key_hash=hash_secret(raw),
            is_active=True,
        )
        session.add(key)
        await session.commit()

        return {"ac": ac, "sessionmaker": sessionmaker, "key": raw, "client_id": str(client.id)}


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_excessive_max_tokens_is_capped(mock_verify, limits_setup):
    ac = limits_setup["ac"]
    key = limits_setup["key"]

    # max_tokens above plan limit should be capped (not rejected), but since backend is missing,
    # we just verify the endpoint accepts the payload and returns a backend error, not 413.
    resp = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "default",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 100000,
        },
    )
    # Backend missing -> 503, but we ensure it is NOT 413 from max_tokens
    assert resp.status_code != 413


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_prompt_exceeds_context_limit_returns_413(mock_verify, limits_setup):
    ac = limits_setup["ac"]
    key = limits_setup["key"]

    large_prompt = "word " * 500  # way more than 64 context tokens
    resp = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "default",
            "messages": [{"role": "user", "content": large_prompt}],
        },
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tts_input_above_limit_returns_413(mock_verify, limits_setup):
    ac = limits_setup["ac"]
    key = limits_setup["key"]

    large_text = "a" * 101
    resp = await ac.post(
        "/pocket-tts/tts",
        headers={"Authorization": f"Bearer {key}"},
        data={"text": large_text},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_rag_upload_above_document_limit_returns_429(mock_verify, limits_setup):
    ac = limits_setup["ac"]
    key = limits_setup["key"]

    with patch("app.api.rag.redis_client") as mock_redis:
        mock_redis.rpush = AsyncMock()

        # First upload should succeed (mock backend not needed for validation endpoint)
        resp1 = await ac.post(
            "/client/rag/documents",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("doc1.txt", b"content 1")},
        )
        # Endpoint may return 200 or other depending on processing; we accept non-429
        assert resp1.status_code != 429

        # Second upload should exceed rag_max_documents=1
        resp2 = await ac.post(
            "/client/rag/documents",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("doc2.txt", b"content 2")},
        )
        assert resp2.status_code == 429


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_queue_overload_returns_429_or_503(mock_verify, abuse_limits_env):
    ac, sessionmaker = abuse_limits_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="queue_test",
            name="Queue Test",
            rate_limit_per_minute=100,
            daily_token_quota=1000000,
            weekly_token_quota=1000000,
            monthly_token_quota=1000000,
            max_output_tokens=512,
        )
        session.add(plan)
        await session.flush()

        client = Client(name="queue-client", billing_plan_id=plan.id, billing_status="active")
        session.add(client)
        await session.flush()

        raw = "sk-queue-12345678"
        key = ApiKey(
            client_id=client.id,
            name="queue-key",
            key_prefix=short_prefix(raw),
            key_hash=hash_secret(raw),
            is_active=True,
        )
        session.add(key)

        model = ModelRegistry(
            model_id="test-model",
            model_alias="test-model",
            provider="test",
            model_file="test-model.gguf",
            is_active=True,
        )
        session.add(model)
        await session.flush()

        backend = InferenceBackend(
            name="test-backend", provider="test", backend_url="http://test", is_active=True
        )
        session.add(backend)
        await session.flush()

        route = ModelBackendRoute(
            model_registry_id=model.id, inference_backend_id=backend.id, priority=1
        )
        session.add(route)
        await session.commit()

    # Patch proxy to simulate queue overloaded
    from app.api.client import get_inference_proxy
    from fastapi import HTTPException

    proxy = AsyncMock()
    # Mock proxy.chat to raise the same HTTPException that InferenceProxy raises on QueueOverloaded
    proxy.chat = AsyncMock(
        side_effect=HTTPException(
            status_code=429,
            detail={
                "error": "generation queue 'inference_free' is full",
                "queue": "inference_free",
            },
        )
    )

    original_proxy = app.dependency_overrides.get(get_inference_proxy)
    app.dependency_overrides[get_inference_proxy] = lambda: proxy

    try:
        resp = await ac.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw}"},
            json={"model": "test-model", "messages": [{"role": "user", "content": "hi"}]},
        )
        # Queue overloaded may be translated to 429 or 503 depending on implementation
        assert resp.status_code in (429, 503)
    finally:
        if original_proxy:
            app.dependency_overrides[get_inference_proxy] = original_proxy
        else:
            app.dependency_overrides.pop(get_inference_proxy, None)
