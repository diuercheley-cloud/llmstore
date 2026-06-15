import uuid

import pytest
from app.models.billing.cost_event import CostEvent
from app.services.billing.cost_attribution import CostAttributionService
from sqlalchemy import select


@pytest.mark.asyncio
async def test_record_cost_event(session):
    service = CostAttributionService(session)
    tenant_id = "test-tenant"
    agent_id = uuid.uuid4()

    event = await service.record_event(
        tenant_id=tenant_id,
        agent_id=agent_id,
        model="gpt-4",
        input_tokens=100,
        output_tokens=50,
        estimated_cost=0.005,
        tool_name="web_search",
    )

    assert event.id is not None
    assert event.tenant_id == tenant_id
    assert event.agent_id == agent_id
    assert event.model == "gpt-4"
    assert event.tool_name == "web_search"
    assert event.estimated_cost == 0.005

    # Verify in DB
    stmt = select(CostEvent).where(CostEvent.id == event.id)
    res = await session.execute(stmt)
    db_event = res.scalar_one()
    assert db_event.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_cost_aggregation_api(admin_client, session):
    # Add some dummy data
    service = CostAttributionService(session)
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"
    agent_1 = uuid.uuid4()

    await service.record_event(tenant_id=tenant_a, agent_id=agent_1, estimated_cost=1.0)
    await service.record_event(tenant_id=tenant_a, agent_id=agent_1, estimated_cost=2.0)
    await service.record_event(tenant_id=tenant_b, estimated_cost=5.0)
    await session.commit()

    headers = {"X-Admin-Token": "test-admin-token"}

    # Test summary
    response = await admin_client.get("/api/admin/costs/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_cost"] == 8.0
    assert data["event_count"] == 3

    # Test by tenant
    response = await admin_client.get("/api/admin/costs/by-tenant", headers=headers)
    assert response.status_code == 200
    tenants = response.json()
    assert any(t["tenant_id"] == tenant_a and t["total_cost"] == 3.0 for t in tenants)
    assert any(t["tenant_id"] == tenant_b and t["total_cost"] == 5.0 for t in tenants)

    # Test by agent
    response = await admin_client.get(
        f"/api/admin/costs/by-agent?tenant_id={tenant_a}", headers=headers
    )
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) == 1
    assert agents[0]["total_cost"] == 3.0
