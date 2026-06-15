import os
import uuid
from pathlib import Path

# Force SQLite for tests
TEST_DB_FILE = Path("/tmp/test-canonical-runtime.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"


import app.db.session
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db, get_db_session
from app.main import app as main_app
from app.models.agents.agents import AgentDefinition, AgentRun, AgentRunEvent
from app.models.core.client import Client
from app.services.auth import require_admin, require_client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Create a fresh engine for tests
engine = create_async_engine(f"sqlite+aiosqlite:///{TEST_DB_FILE}", pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Patch the global session and engine to avoid PostgreSQL attempts in background services
app.db.session.engine = engine
app.db.session.SessionLocal = SessionLocal


async def override_get_db():
    async with SessionLocal() as session:
        yield session


main_app.dependency_overrides[get_db] = override_get_db
main_app.dependency_overrides[get_db_session] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Disable eval baseline requirement for tests to avoid 403
    settings = get_settings()
    orig_eval_req = settings.agent_production_requires_eval_baseline
    settings.agent_production_requires_eval_baseline = False

    # Ensure runtime is enabled
    orig_runtime = settings.agent_runtime_enabled
    orig_plane = settings.agent_execution_plane_enabled
    settings.agent_runtime_enabled = True
    settings.agent_execution_plane_enabled = True

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    settings.agent_production_requires_eval_baseline = orig_eval_req
    settings.agent_runtime_enabled = orig_runtime
    settings.agent_execution_plane_enabled = orig_plane
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Mock Clients
CLIENT_1_ID = uuid.uuid4()
CLIENT_2_ID = uuid.uuid4()


async def mock_require_client_1():
    return Client(id=CLIENT_1_ID, name="Client 1")


async def mock_require_client_2():
    return Client(id=CLIENT_2_ID, name="Client 2")


async def mock_require_admin():
    return {"role": "super_admin"}


@pytest_asyncio.fixture
async def setup_agents():
    async with SessionLocal() as db:
        # Create agents for both clients
        agent1 = AgentDefinition(
            id=uuid.uuid4(),
            name="Agent Client 1",
            tenant_id=str(CLIENT_1_ID),
            status="active",
            instructions="Test",
            model_id="gpt-3.5-turbo",
            owner="admin",
            version="1.0.0",
        )
        agent2 = AgentDefinition(
            id=uuid.uuid4(),
            name="Agent Client 2",
            tenant_id=str(CLIENT_2_ID),
            status="active",
            instructions="Test",
            model_id="gpt-3.5-turbo",
            owner="admin",
            version="1.0.0",
        )
        db.add(agent1)
        db.add(agent2)
        await db.commit()
        return agent1.id, agent2.id


pytest_mark_asyncio = pytest.mark.asyncio


@pytest_mark_asyncio
async def test_v1_agents_start_run_tenant_isolation(async_client, setup_agents):
    agent1_id, agent2_id = setup_agents

    # 1. Test Client 1 accessing Agent 1 (Success)
    main_app.dependency_overrides[require_client] = mock_require_client_1
    response = await async_client.post(f"/v1/agents/{agent1_id}/runs", json={"input_text": "Hello"})
    assert response.status_code == 200
    run_data = response.json()
    assert "id" in run_data

    # Verify DB records
    async with SessionLocal() as db:
        run_id = uuid.UUID(run_data["id"])
        run = await db.get(AgentRun, run_id)
        assert run is not None
        assert run.tenant_id == str(CLIENT_1_ID)

        # Check for events
        stmt = select(AgentRunEvent).where(AgentRunEvent.run_id == run_id)
        res = await db.execute(stmt)
        events = res.scalars().all()
        assert len(events) > 0
        assert any(e.event_type == "run_started" for e in events)

    # 2. Test Client 1 accessing Agent 2 (Failure - Isolation)
    response = await async_client.post(f"/v1/agents/{agent2_id}/runs", json={"input_text": "Hello"})
    assert response.status_code == 404


@pytest_mark_asyncio
async def test_legacy_agents_deprecation_and_unification(async_client, setup_agents):
    agent1_id, agent2_id = setup_agents
    main_app.dependency_overrides[require_admin] = mock_require_admin

    # Test POST /agents/{id}/runs
    payload = {"tenant_id": str(CLIENT_1_ID), "input_text": "Legacy call"}
    response = await async_client.post(f"/agents/{agent1_id}/runs", json=payload)

    # Verify Deprecation Headers
    assert response.headers["X-Deprecated-Endpoint"] == "true"
    assert response.headers["X-Replacement-Endpoint"] == "/v1/agents"

    assert response.status_code == 200
    run_data = response.json()

    # Verify unification - same run created
    async with SessionLocal() as db:
        run_id = uuid.UUID(run_data["id"])
        run = await db.get(AgentRun, run_id)
        assert run is not None
        assert run.tenant_id == str(CLIENT_1_ID)


@pytest_mark_asyncio
async def test_v1_agents_get_run_isolation(async_client, setup_agents):
    agent1_id, agent2_id = setup_agents

    # Create run for Client 2
    main_app.dependency_overrides[require_client] = mock_require_client_2
    response = await async_client.post(f"/v1/agents/{agent2_id}/runs", json={"input_text": "Hello"})
    run_id = response.json()["id"]

    # Try to access it with Client 1
    main_app.dependency_overrides[require_client] = mock_require_client_1
    response = await async_client.get(f"/v1/agents/runs/{run_id}")
    assert response.status_code == 404


@pytest_mark_asyncio
async def test_admin_can_see_all_runs_in_legacy(async_client, setup_agents):
    agent1_id, agent2_id = setup_agents
    main_app.dependency_overrides[require_admin] = mock_require_admin

    # Create runs for both tenants
    main_app.dependency_overrides[require_client] = mock_require_client_1
    await async_client.post(f"/v1/agents/{agent1_id}/runs", json={"input_text": "R1"})

    main_app.dependency_overrides[require_client] = mock_require_client_2
    await async_client.post(f"/v1/agents/{agent2_id}/runs", json={"input_text": "R2"})

    # Admin lists all runs
    main_app.dependency_overrides[require_admin] = mock_require_admin
    response = await async_client.get("/agents/runs")
    assert response.status_code == 200
    runs = response.json()

    tenant_ids = [r["tenant_id"] for r in runs]
    assert str(CLIENT_1_ID) in tenant_ids
    assert str(CLIENT_2_ID) in tenant_ids

    # Admin filters by tenant
    response = await async_client.get(f"/agents/runs?tenant_id={CLIENT_1_ID}")
    runs = response.json()
    for r in runs:
        assert r["tenant_id"] == str(CLIENT_1_ID)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    main_app.dependency_overrides = {}
