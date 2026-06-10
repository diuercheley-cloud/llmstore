import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.agent_incidents import AgentIncidentService
from app.services.agents.agent_observability import AgentObservabilityService
from app.services.agents.agent_slo import AgentSLOService
from app.services.agents.agent_trace_correlation import AgentTraceCorrelationService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents.agents  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def _create_test_agent(db: AsyncSession):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="ObsAgent",
        version="1.0.0",
        model_id="mock",
        owner="test",
        tenant_id="t1",
        status="active"
    )
    db.add(agent)
    await db.commit()
    return agent

@pytest.mark.asyncio
async def test_incident_created_on_handoff_loop():
    async with SessionLocal() as db:
        agent = await _create_test_agent(db)
        svc = AgentIncidentService(db)
        
        inc = await svc.detect_and_create_incident(
            "t1", agent.id, None, "handoff_loop", "Agent stuck in handoff loop"
        )
        assert inc is not None
        assert inc.incident_type == "handoff_loop"
        assert inc.status == "open"

@pytest.mark.asyncio
async def test_trace_correlation_links():
    async with SessionLocal() as db:
        agent = await _create_test_agent(db)
        run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_data={})
        db.add(run)
        await db.commit()
        
        svc = AgentTraceCorrelationService(db)
        await svc.link_traces(run.id, "trace-1", "trace-2", "handoff")
        
        corr = await svc.get_run_correlation(run.id)
        assert len(corr["links"]) == 1
        assert corr["links"][0]["reason"] == "handoff"

@pytest.mark.asyncio
async def test_prompt_redaction_in_observability():
    async with SessionLocal() as db:
        agent = await _create_test_agent(db)
        run_id = uuid.uuid4()
        svc = AgentObservabilityService(db)
        
        # This will add to session but not commit
        await svc._record_timeline_event(run_id, "run.started", {"prompt": "my secret prompt", "other": "val"})
        await db.commit()
        
        from app.models.agents.agents import AgentTimelineEvent
        from sqlalchemy import select
        res = await db.execute(select(AgentTimelineEvent).where(AgentTimelineEvent.run_id == run_id))
        event = res.scalar_one()
        
        assert "prompt" not in event.details_json
        assert event.details_json["other"] == "val"

@pytest.mark.asyncio
async def test_slo_breach_calculation():
    async with SessionLocal() as db:
        agent = await _create_test_agent(db)
        
        # Create 10 runs, 5 failed
        for i in range(5):
            db.add(AgentRun(agent_id=agent.id, tenant_id="t1", status="completed", input_data={}))
        for i in range(5):
            db.add(AgentRun(agent_id=agent.id, tenant_id="t1", status="failed", input_data={}))
        await db.commit()
        
        svc = AgentSLOService(db)
        window = await svc.calculate_slo_window(agent.id, "24h")
        
        assert window.slo_breached is True
        assert window.metrics_json["success_rate"] == 0.5
