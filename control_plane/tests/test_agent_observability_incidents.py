import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.agents import AgentDefinition, AgentRun
from app.services.agents.agent_cost_meter import AgentCostMeterService
from app.services.agents.agent_incidents import AgentIncidentService
from app.services.agents.agent_run_timeline import AgentRunTimelineService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def client():
    # Mock auth for admin
    from app.api.deps import require_admin
    class MockAdmin:
        email = "admin@example.com"
        roles = ["admin"]
        
    app.dependency_overrides[require_admin] = lambda: MockAdmin()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

async def _create_test_data(db: AsyncSession):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="ObservabilityTestAgent",
        version="1.0.0",
        description="Test",
        instructions="Test",
        model_id="mock-model",
        owner="test-owner",
        tenant_id="test-tenant",
        status="active"
    )
    db.add(agent)
    
    run = AgentRun(
        id=uuid.uuid4(),
        agent_id=agent.id,
        tenant_id="test-tenant",
        status="completed",
        input_data={"prompt": "do it"},
        output_data={"answer": "done"}
    )
    db.add(run)
    await db.commit()
    return agent, run

@pytest.mark.asyncio
async def test_timeline_ordered():
    async with SessionLocal() as db:
        agent, run = await _create_test_data(db)
        svc = AgentRunTimelineService(db)
        
        await svc.record_event(run.id, "run.started")
        await svc.record_event(run.id, "tool.called", tool_name="search")
        await svc.record_event(run.id, "run.completed")
        
        timeline = await svc.get_timeline(run.id)
        assert len(timeline) == 3
        assert timeline[0].event_type == "run.started"
        assert timeline[1].event_type == "tool.called"
        assert timeline[2].event_type == "run.completed"

@pytest.mark.asyncio
async def test_cost_registered():
    async with SessionLocal() as db:
        agent, run = await _create_test_data(db)
        svc = AgentCostMeterService(db)
        
        await svc.record_cost("test-tenant", agent.id, run.id, 10, 20, 0.5)
        await svc.record_cost("test-tenant", agent.id, run.id, 5, 10, 0.25)
        
        cost = await svc.get_cost(run.id)
        assert cost.prompt_tokens == 15
        assert cost.completion_tokens == 30
        assert cost.estimated_cost_brl == 0.75

@pytest.mark.asyncio
async def test_incident_created_run_stuck():
    async with SessionLocal() as db:
        agent, run = await _create_test_data(db)
        svc = AgentIncidentService(db)
        
        inc = await svc.detect_and_create_incident(
            "test-tenant", agent.id, run.id, "run_stuck", "Run is stuck for 5 mins"
        )
        assert inc is not None
        assert inc.status == "open"
        assert inc.incident_type == "run_stuck"

@pytest.mark.asyncio
async def test_incident_created_policy_denial_spike():
    async with SessionLocal() as db:
        agent, run = await _create_test_data(db)
        svc = AgentIncidentService(db)
        
        inc = await svc.detect_and_create_incident(
            "test-tenant", agent.id, run.id, "policy_denial_spike", "Agent repeatedly denied by policy"
        )
        assert inc is not None
        assert inc.incident_type == "policy_denial_spike"

def test_api_incident_endpoints(client):
    import asyncio
    
    # We must insert an incident directly or use the service for the test
    async def create_incident():
        async with SessionLocal() as db:
            agent, run = await _create_test_data(db)
            svc = AgentIncidentService(db)
            inc = await svc.detect_and_create_incident("t1", agent.id, run.id, "test", "Test Incident")
            return str(inc.id)
            
    incident_id = asyncio.run(create_incident())
    
    # 1. Get incidents
    r = client.get("/admin/agents/incidents")
    assert r.status_code == 200
    assert len(r.json()) > 0
    
    # 2. Ack
    r = client.post(f"/admin/agents/incidents/{incident_id}/ack")
    assert r.status_code == 200
    assert r.json()["status"] == "acknowledged"
    
    # 3. Resolve
    r = client.post(f"/admin/agents/incidents/{incident_id}/resolve", json={"resolution_notes": "Fixed it"})
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    assert r.json()["resolution_notes"] == "Fixed it"

@pytest.mark.asyncio
async def test_exports_sanitized():
    async with SessionLocal() as db:
        agent, run = await _create_test_data(db)
        svc = AgentRunTimelineService(db)
        
        event = await svc.record_event(
            run.id, "tool.called", details={"input": "my secret is 123"}
        )
        
        assert "sanitized" in event.details_json
        assert "secret" not in event.details_json.get("input", "")
