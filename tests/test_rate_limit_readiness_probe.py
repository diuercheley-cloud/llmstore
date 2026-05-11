import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.model_registry import ModelRegistry
from app.models.inference_backend import InferenceBackend
from app.core.security import hash_secret, short_prefix
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_rate_limit_readiness_probe_triggers_429(isolated_db_url, fake_redis):
    # Setup similar to abuse_limits_env but specific for this probe
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.db.base import Base
    
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    from app.api.deps import get_inference_proxy
    import json as json_lib
    mock_proxy = AsyncMock()
    mock_result = MagicMock()
    mock_result.response.status_code = 200
    mock_result.response.body = json_lib.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
    mock_result.backend_name = "mock-backend"
    mock_proxy.chat.return_value = mock_result
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_inference_proxy] = lambda: mock_proxy

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        # 1. Create the low-limit plan, backend and model
        async with testing_session_local() as session:
            plan = BillingPlan(
                code="readiness-rate-limit-test",
                name="Readiness Rate Limit Test",
                rate_limit_per_minute=2,
                daily_token_quota=1000,
                weekly_token_quota=5000,
                monthly_token_quota=10000,
                max_output_tokens=64
            )
            session.add(plan)
            await session.commit()
            await session.refresh(plan)
            plan_id = plan.id

            client = Client(name="test-readiness-client", billing_plan_id=plan_id, billing_status="active")
            session.add(client)
            await session.commit()
            await session.refresh(client)
            client_id = client.id

            backend = InferenceBackend(
                name="test-backend",
                provider="mock",
                backend_url="http://test",
                is_active=True
            )
            session.add(backend)
            await session.commit()
            await session.refresh(backend)

            model = ModelRegistry(
                model_id="test-model",
                model_alias="test-model",
                provider="mock",
                model_file="test.gguf",
                inference_backend_id=backend.id,
                is_active=True,
                is_default=True
            )
            session.add(model)

            raw_key = "sk-readiness-probe-test-123"  # FAKE TEST KEY - DO NOT USE
            api_key = ApiKey(
                client_id=client_id,
                name="test-key",
                key_prefix=short_prefix(raw_key),
                key_hash=hash_secret(raw_key)
            )
            session.add(api_key)
            await session.commit()

        # 2. Perform requests to trigger rate limit
        headers = {"Authorization": f"Bearer {raw_key}"}
        payload = {"model": "test-model", "prompt": "hi", "max_tokens": 5}
        
        # Request 1: Should be 200
        resp1 = await ac.post("/portal/test-chat", headers=headers, json=payload)
        assert resp1.status_code == 200
        
        # Request 2: Should be 200
        resp2 = await ac.post("/portal/test-chat", headers=headers, json=payload)
        assert resp2.status_code == 200
        
        # Request 3: Should be 429
        resp3 = await ac.post("/portal/test-chat", headers=headers, json=payload)
        assert resp3.status_code == 429

    app.dependency_overrides.clear()
    await engine.dispose()
