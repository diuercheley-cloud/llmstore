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
async def test_routing_explain_endpoint(
    admin_client: AsyncClient, admin_token_headers: dict, session: AsyncSession
):
    # 1. Setup Data
    plan = BillingPlan(
        code="premium-vllm",
        name="Premium VLLM Plan",
        rate_limit_per_minute=60,
        daily_token_quota=1000000,
        weekly_token_quota=5000000,
        monthly_token_quota=20000000,
        max_output_tokens=4096,
        routing_policy_json=json.dumps(
            {
                "rules": [
                    {"action": "prioritize_backend_type", "value": "vllm", "priority_boost": 50}
                ]
            }
        ),
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    test_client = Client(name="test-routing-client", billing_plan_id=plan.id)
    session.add(test_client)

    backend_vllm = InferenceBackend(name="vllm-backend", provider="vllm", backend_url="http://vllm")
    backend_llama = InferenceBackend(
        name="llama-backend", provider="llama.cpp", backend_url="http://llama"
    )
    session.add(backend_vllm)
    session.add(backend_llama)
    await session.commit()
    await session.refresh(backend_vllm)
    await session.refresh(backend_llama)

    model = ModelRegistry(
        model_id="test-model",
        provider="llama.cpp",
        model_file="test.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)

    route1 = ModelBackendRoute(
        model_registry_id=model.id, inference_backend_id=backend_vllm.id, priority=100, weight=100
    )
    route2 = ModelBackendRoute(
        model_registry_id=model.id, inference_backend_id=backend_llama.id, priority=100, weight=100
    )
    session.add(route1)
    session.add(route2)
    await session.commit()

    # 2. Call Explain
    res = await admin_client.post(
        "/admin/routing/explain",
        json={"model": "test-model", "client_id": str(test_client.id)},
        headers=admin_token_headers,
    )

    assert res.status_code == 200
    data = res.json()
    assert data["resolved_model_id"] == "test-model"
    assert data["plan_code"] == "premium-vllm"
    assert data["chosen_backend"] == "vllm-backend"
    assert len(data["candidates_order"]) == 2
    assert data["candidates_order"][0]["backend_name"] == "vllm-backend"
    assert data["candidates_order"][0]["priority"] == 50  # 100 - 50 boost
