import json

import pytest
import pytest_asyncio
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_unauthorized_model_rewrite_to_default(
    admin_client: AsyncClient, admin_token_headers: dict, session: AsyncSession
):
    # 1. Setup Default Model
    default_model = ModelRegistry(
        model_id="default-model",
        provider="llama.cpp",
        model_file="default.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
    )
    session.add(default_model)

    premium_model = ModelRegistry(
        model_id="premium-model",
        provider="llama.cpp",
        model_file="premium.gguf",
        context_length=2048,
        is_active=True,
        is_default=False,
    )
    session.add(premium_model)

    backend = InferenceBackend(name="main-backend", provider="llama.cpp", backend_url="http://main")
    session.add(backend)
    await session.commit()
    await session.refresh(default_model)
    await session.refresh(premium_model)
    await session.refresh(backend)

    # Routes for both
    session.add(
        ModelBackendRoute(
            model_registry_id=default_model.id,
            inference_backend_id=backend.id,
            priority=100,
            weight=100,
        )
    )
    session.add(
        ModelBackendRoute(
            model_registry_id=premium_model.id,
            inference_backend_id=backend.id,
            priority=100,
            weight=100,
        )
    )

    # 2. Client on Restricted Plan (only default model allowed)
    plan = BillingPlan(
        code="free",
        name="Free Plan",
        rate_limit_per_minute=10,
        daily_token_quota=1000,
        weekly_token_quota=5000,
        monthly_token_quota=10000,
        max_output_tokens=1024,
        allowed_models_json=json.dumps(["default-model"]),
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    test_client = Client(name="free-client", billing_plan_id=plan.id)
    session.add(test_client)
    await session.commit()
    await session.refresh(test_client)

    # 3. Request unauthorized model via Explain
    res = await admin_client.post(
        "/admin/routing/explain",
        json={"model": "premium-model", "client_id": str(test_client.id)},
        headers=admin_token_headers,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["requested_model"] == "premium-model"
    assert data["resolved_model_id"] == "default-model"  # Rewritten!
