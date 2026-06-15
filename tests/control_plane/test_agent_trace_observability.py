import uuid
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.telemetry.agent_trace_service import AgentTraceService
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = Path("/tmp/test-agent-trace-observability.db")


@pytest_asyncio.fixture(autouse=True)
async def test_db():
    db_url = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    await engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass


@pytest.fixture
def client():
    from app.api.deps import require_admin

    class MockAdmin:
        email = "admin@example.com"
        roles = ["admin"]

    fastapi_app.dependency_overrides[require_admin] = lambda: MockAdmin()
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agent_trace_creation(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(),
            name="TraceTestAgent",
            version="1.0.0",
            description="Test description",
            instructions="Test instructions",
            model_id="mock-model",
            owner="test-owner",
            tenant_id="test-tenant",
            status="active",
        )
        db.add(agent)

        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="test-tenant", status="running"
        )
        db.add(run)
        await db.commit()

        # Capture a reasoning step
        trace_reasoning = await AgentTraceService.create_trace(
            db=db,
            run_id=run.id,
            trace_type="reasoning_step",
            name="step_1_reasoning",
            input_data={"prompt": "hello"},
            output_data={"thought": "say hello"},
            status="success",
        )
        assert trace_reasoning.run_id == run.id
        assert trace_reasoning.trace_type == "reasoning_step"
        assert trace_reasoning.name == "step_1_reasoning"
        assert trace_reasoning.status == "success"

        # Capture a tool call
        trace_tool = await AgentTraceService.create_trace(
            db=db,
            run_id=run.id,
            trace_type="tool_call",
            name="calculator",
            input_data={"formula": "2+2"},
            output_data={"result": "4"},
            status="success",
        )
        assert trace_tool.trace_type == "tool_call"
        assert trace_tool.name == "calculator"

        # Capture a memory read
        trace_mem_read = await AgentTraceService.create_trace(
            db=db,
            run_id=run.id,
            trace_type="memory_read",
            name="memory_read_short_term",
            input_data={"key": "context"},
            output_data={"value": "some context"},
            status="success",
        )
        assert trace_mem_read.trace_type == "memory_read"

        # Capture a retry
        trace_retry = await AgentTraceService.create_trace(
            db=db,
            run_id=run.id,
            trace_type="retry",
            name="execution_retry_1",
            input_data={"attempt": 1},
            status="success",
        )
        assert trace_retry.trace_type == "retry"


@pytest.mark.asyncio
async def test_timeline_endpoint_with_traces(test_db, client):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(),
            name="TimelineTestAgent",
            version="1.0.0",
            description="Test",
            instructions="Test",
            model_id="mock-model",
            owner="test-owner",
            tenant_id="test-tenant",
            status="active",
        )
        db.add(agent)

        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="test-tenant", status="completed"
        )
        db.add(run)
        await db.commit()

        # Create traces
        await AgentTraceService.create_trace(
            db=db, run_id=run.id, trace_type="reasoning_step", name="step_1", status="success"
        )
        await AgentTraceService.create_trace(
            db=db, run_id=run.id, trace_type="tool_call", name="calculator", status="success"
        )

    # Call timeline API
    response = client.get(f"/admin/agents/observability/runs/{run.id}/timeline")
    assert response.status_code == 200
    timeline = response.json()

    # Assert new trace types are part of the timeline
    trace_types = [item["step_type"] for item in timeline if item["type"] == "step"]
    assert "reasoning_step" in trace_types
    assert "tool_call" in trace_types


@pytest.mark.asyncio
async def test_replay_run_endpoint(test_db, client):
    settings = get_settings()
    settings.agent_replay_enabled = True

    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(),
            name="ReplayTestAgent",
            version="1.0.0",
            description="Test",
            instructions="Test",
            model_id="mock-model",
            owner="test-owner",
            tenant_id="test-tenant",
            status="active",
        )
        db.add(agent)

        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="test-tenant", status="completed"
        )
        db.add(run)
        await db.commit()

    # Call replay endpoint
    response = client.post(f"/admin/agents/observability/runs/{run.id}/replay")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == str(run.id)
    assert data["agent_id"] == str(agent.id)
