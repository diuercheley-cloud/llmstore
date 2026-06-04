from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.security import hash_secret, short_prefix
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.main import app
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.models.inference_backend import InferenceBackend
from app.models.model_registry import ModelRegistry
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def abuse_payload_env(isolated_db_url, fake_redis):
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    with patch("app.db.session.SessionLocal", testing_session_local), \
         patch("app.services.backend_slot_manager.SessionLocal", testing_session_local), \
         patch("app.services.backend_slot_manager.BackendSlotManager.try_acquire", return_value=True), \
         patch("app.services.backend_slot_manager.BackendSlotManager.release", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            yield ac, testing_session_local

    app.dependency_overrides.clear()
    await engine.dispose()



@pytest_asyncio.fixture
async def payload_setup(abuse_payload_env):
    ac, sessionmaker = abuse_payload_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="payload_test",
            name="Payload Test",
            rate_limit_per_minute=100,
            daily_token_quota=100000,
            weekly_token_quota=100000,
            monthly_token_quota=100000,
            max_output_tokens=512,
            allow_streaming=True,
            embeddings_enabled=True,
            embeddings_requests_per_month=100,
            embeddings_tokens_per_month=10000,
            embeddings_max_inputs_per_request=5,
        )
        session.add(plan)
        await session.flush()

        client = Client(name="payload-client", billing_plan_id=plan.id, billing_status="active")
        session.add(client)
        await session.flush()

        # Add a default model so resolve_requested_model doesn't fail with 503
        backend = InferenceBackend(name="test-backend", provider="test", backend_url="http://test", is_active=True)
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

        raw = "sk-payload-12345678"
        key = ApiKey(
            client_id=client.id,
            name="payload-key",
            key_prefix=short_prefix(raw),
            key_hash=hash_secret(raw),
            is_active=True,
        )
        session.add(key)
        await session.commit()

        return {"ac": ac, "key": raw}


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_invalid_json_payload_returns_422(mock_verify, payload_setup):
    ac = payload_setup["ac"]
    key = payload_setup["key"]

    resp = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        data="this is not json",
    )
    # FastAPI returns 422 for malformed JSON when Content-Type is application/json
    assert resp.status_code == 422


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_giant_prompt_returns_413(mock_verify, abuse_payload_env):
    ac, sessionmaker = abuse_payload_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="giant_test",
            name="Giant Test",
            rate_limit_per_minute=100,
            daily_token_quota=100000,
            weekly_token_quota=100000,
            monthly_token_quota=100000,
            max_output_tokens=512,
        )
        session.add(plan)
        await session.flush()

        client = Client(name="giant-client", billing_plan_id=plan.id, billing_status="active", max_context_tokens=50)
        session.add(client)
        await session.flush()

        backend = InferenceBackend(name="giant-backend", provider="test", backend_url="http://test", is_active=True)
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

        raw = "sk-giant-12345678"
        key = ApiKey(
            client_id=client.id,
            name="giant-key",
            key_prefix=short_prefix(raw),
            key_hash=hash_secret(raw),
            is_active=True,
        )
        session.add(key)
        await session.commit()

    giant_prompt = "word " * 200  # exceeds 50 context tokens
    resp = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "default", "messages": [{"role": "user", "content": giant_prompt}]},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_embeddings_too_many_inputs_returns_400(mock_verify, payload_setup):
    ac = payload_setup["ac"]
    key = payload_setup["key"]

    resp = await ac.post(
        "/v1/embeddings",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "text-embedding-3-small",
            "input": ["a", "b", "c", "d", "e", "f"],  # exceeds embeddings_max_inputs_per_request=5
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_streaming_not_allowed_for_plan_returns_403(mock_verify, abuse_payload_env):
    ac, sessionmaker = abuse_payload_env

    async with sessionmaker() as session:
        plan = BillingPlan(
            code="no_stream",
            name="No Stream",
            rate_limit_per_minute=100,
            daily_token_quota=100000,
            weekly_token_quota=100000,
            monthly_token_quota=100000,
            max_output_tokens=512,
            allow_streaming=False,
        )
        session.add(plan)
        await session.flush()

        client = Client(name="no-stream-client", billing_plan_id=plan.id, billing_status="active")
        session.add(client)
        await session.flush()

        backend = InferenceBackend(name="no-stream-backend", provider="test", backend_url="http://test", is_active=True)
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

        raw = "sk-nostream-12345678"
        key = ApiKey(
            client_id=client.id,
            name="no-stream-key",
            key_prefix=short_prefix(raw),
            key_hash=hash_secret(raw),
            is_active=True,
        )
        session.add(key)
        await session.commit()

    resp = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw}"},
        json={"model": "default", "messages": [{"role": "user", "content": "hi"}], "stream": True},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_interrupted_stream_request_is_accepted_or_errors_gracefully(mock_verify, payload_setup):
    ac = payload_setup["ac"]
    key = payload_setup["key"]

    # Since there is no real backend in unit tests, we just verify that the endpoint
    # does not crash with stream=true and returns a controlled error (503) or processes it.
    resp = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": "default", "messages": [{"role": "user", "content": "hi"}], "stream": True},
    )
    # Without backend, expect 503 or 200 if mocked; ensure NOT 500
    assert resp.status_code != 500
