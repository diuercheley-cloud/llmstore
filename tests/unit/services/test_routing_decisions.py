from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from app.models.core.inference_routing_decision import InferenceRoutingDecision
from app.models.core.inference_backend import InferenceBackend
from app.services.inference.router import InferenceRouter
from app.services.inference_backends import Capability
from sqlalchemy import select

@pytest.mark.asyncio
async def test_inference_router_successful_routing(session):
    # Setup active backend
    backend = InferenceBackend(
        name="gpu-vllm",
        provider="vllm",
        backend_url="http://localhost:8000",
        is_active=True
    )
    session.add(backend)
    await session.commit()
    
    router = InferenceRouter(session)
    adapter, reason = await router.get_best_backend(
        model_name="meta-llama-3",
        capability=Capability.CHAT,
        tenant_id="tenant-123",
        request_id="req-abc",
        client_id="client-xyz",
        latency_ms=150,
        success=True
    )
    assert adapter is not None
    assert adapter.name == "gpu-vllm"
    
    # Query database and check decision
    session.expire_all()
    db_res = await session.execute(
        select(InferenceRoutingDecision)
        .where(InferenceRoutingDecision.request_id == "req-abc")
        .execution_options(populate_existing=True)
    )
    decision = db_res.scalars().first()
    assert decision is not None
    assert decision.tenant_id == "tenant-123"
    assert decision.client_id == "client-xyz"
    assert decision.selected_backend == "gpu-vllm"
    assert decision.selected_model == "meta-llama-3"
    assert decision.success is True
    assert decision.latency_ms == 150
    assert "gpu-vllm" in decision.candidate_backends["backends"]


@pytest.mark.asyncio
async def test_inference_router_failed_routing(session):
    # No active backends in session
    router = InferenceRouter(session)
    adapter, reason = await router.get_best_backend(
        model_name="unsupported-model",
        capability=Capability.CHAT,
        request_id="req-failed-1"
    )
    assert adapter is None
    
    session.expire_all()
    db_res = await session.execute(
        select(InferenceRoutingDecision)
        .where(InferenceRoutingDecision.request_id == "req-failed-1")
        .execution_options(populate_existing=True)
    )
    decision = db_res.scalars().first()
    assert decision is not None
    assert decision.success is False
    assert decision.error_code == "NO_ACTIVE_BACKENDS"


@pytest.mark.asyncio
async def test_inference_router_retention_cleanup(session):
    now = datetime.now(timezone.utc)
    
    # 1. Old decision (40 days ago)
    old_decision = InferenceRoutingDecision(
        request_id="req-old",
        selected_model="gpt-3.5",
        success=True,
        created_at=now - timedelta(days=40)
    )
    
    # 2. New decision (2 days ago)
    new_decision = InferenceRoutingDecision(
        request_id="req-new",
        selected_model="gpt-4",
        success=True,
        created_at=now - timedelta(days=2)
    )
    
    session.add(old_decision)
    session.add(new_decision)
    await session.commit()
    
    router = InferenceRouter(session)
    
    # Perform cleanup for > 30 days
    deleted_count = await router.cleanup_old_decisions(retention_days=30)
    assert deleted_count == 1
    await session.commit()
    
    # Verify DB state
    session.expire_all()
    db_res = await session.execute(
        select(InferenceRoutingDecision)
        .execution_options(populate_existing=True)
    )
    remaining_decisions = db_res.scalars().all()
    assert len(remaining_decisions) == 1
    assert remaining_decisions[0].request_id == "req-new"
