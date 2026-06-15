from __future__ import annotations

import pytest
from app.models.core.inference_backend import InferenceBackend
from app.models.core.inference_routing_decision import InferenceRoutingDecision
from sqlalchemy import select


@pytest.mark.asyncio
async def test_admin_inference_routing_endpoints(admin_client, admin_token_headers, session):
    # Seed an active backend first so the router has something to select
    backend = InferenceBackend(
        name="test-vllm", provider="vllm", backend_url="http://localhost:8000", is_active=True
    )
    session.add(backend)
    await session.commit()

    # 1. Simulate routing
    sim_resp = await admin_client.post(
        "/admin/inference/routing/simulate",
        headers=admin_token_headers,
        params={"model": "gpt-4", "capability": "chat", "tenant_id": "tenant-abc"},
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["selected_backend"] == "test-vllm"

    # Verify the decision was persisted in the DB
    session.expire_all()
    db_res = await session.execute(
        select(InferenceRoutingDecision)
        .where(InferenceRoutingDecision.selected_model == "gpt-4")
        .execution_options(populate_existing=True)
    )
    decision = db_res.scalars().first()
    assert decision is not None
    assert decision.selected_backend == "test-vllm"
    assert decision.tenant_id == "tenant-abc"
    assert decision.success is True

    # 2. Query history/last-decision endpoint
    history_resp = await admin_client.get(
        "/admin/inference/routing/last-decision", headers=admin_token_headers
    )
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert len(history_data["log"]) >= 1
    assert history_data["log"][0]["selected_model"] == "gpt-4"
    assert history_data["last_decision"]["selected_backend"] == "test-vllm"
