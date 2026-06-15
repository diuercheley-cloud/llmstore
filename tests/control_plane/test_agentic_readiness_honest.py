import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.main import app as main_app
from app.models.agents.agents import AgentRun
from app.services.auth import require_admin
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def mock_require_admin():
    return {"role": "super_admin"}


@pytest_asyncio.fixture
async def test_db():
    db_file = Path(f"/tmp/test-readiness-{uuid.uuid4()}.db")
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Patch
    orig_engine = app.db.session.engine
    orig_session = app.db.session.SessionLocal
    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    await engine.dispose()
    if db_file.exists():
        try:
            db_file.unlink()
        except:
            pass

    app.db.session.engine = orig_engine
    app.db.session.SessionLocal = orig_session


@pytest.mark.asyncio
async def test_readiness_runtime_disabled(async_client, test_db):
    settings = get_settings()
    orig_enabled = settings.agent_runtime_enabled
    settings.agent_runtime_enabled = False

    main_app.dependency_overrides[require_admin] = mock_require_admin

    try:
        response = await async_client.get("/admin/agents/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
        assert any(c["id"] == "runtime_enabled" and c["status"] == "fail" for c in data["checks"])
    finally:
        settings.agent_runtime_enabled = orig_enabled
        main_app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_readiness_worker_enabled_no_heartbeat(async_client, test_db):
    settings = get_settings()
    orig_runtime = settings.agent_runtime_enabled
    orig_worker = settings.agent_worker_enabled
    settings.agent_runtime_enabled = True
    settings.agent_worker_enabled = True

    main_app.dependency_overrides[require_admin] = mock_require_admin

    try:
        # No heartbeats in DB
        response = await async_client.get("/admin/agents/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "blocked"
        assert any(c["id"] == "worker_heartbeat" and c["status"] == "fail" for c in data["checks"])
        assert (
            "No active agent workers detected while AGENT_WORKER_ENABLED is true."
            in data["blockers"]
        )
    finally:
        settings.agent_runtime_enabled = orig_runtime
        settings.agent_worker_enabled = orig_worker
        main_app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_readiness_stuck_runs(async_client, test_db):
    session_factory = test_db
    settings = get_settings()
    orig_runtime = settings.agent_runtime_enabled
    settings.agent_runtime_enabled = True

    main_app.dependency_overrides[require_admin] = mock_require_admin

    async with session_factory() as db:
        # Create a stuck run (running for > 1 hour)
        stuck_run = AgentRun(
            id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            tenant_id="test-tenant",
            status="running",
            started_at=datetime.now(UTC) - timedelta(hours=2),
            total_steps=1,
            total_tokens=0,
            estimated_cost_brl=0.0,
        )
        db.add(stuck_run)
        await db.commit()

    try:
        response = await async_client.get("/admin/agents/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert any(c["id"] == "stuck_runs" and c["status"] == "fail" for c in data["checks"])
        assert "1 stuck runs detected" in data["warnings"]
    finally:
        settings.agent_runtime_enabled = orig_runtime
        main_app.dependency_overrides = {}
