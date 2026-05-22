import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.agents import AgentRun, AgentIncident
from app.models.agent_execution import AgentWorkerHeartbeat
from app.services.agents.agent_readiness import AgentReadinessService

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_readiness_degraded_worker_down():
    async with SessionLocal() as db:
        # No heartbeats -> degraded (active_workers = 0)
        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert res["status"] == "degraded"
        assert res["checks"]["active_workers"]["status"] == "warn"

@pytest.mark.asyncio
async def test_readiness_unhealthy_critical_incident():
    async with SessionLocal() as db:
        # Create critical incident
        inc = AgentIncident(
            tenant_id="t1",
            agent_id=uuid.uuid4(),
            incident_type="memory_isolation_violation",
            title="CRITICAL",
            severity="critical",
            status="open"
        )
        db.add(inc)
        await db.commit()
        
        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert res["status"] == "unhealthy"
        assert res["checks"]["critical_incidents"]["status"] == "fail"

@pytest.mark.asyncio
async def test_readiness_pass_all():
    async with SessionLocal() as db:
        # Add heartbeat
        hb = AgentWorkerHeartbeat(
            worker_id="w1",
            last_heartbeat=datetime.now(datetime.timezone.utc)
        )
        db.add(hb)
        await db.commit()
        
        # Override settings for test
        from app.core.config import get_settings
        settings = get_settings()
        settings.agent_runtime_enabled = True
        
        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        # Since we have hb and no incidents/stuck runs
        assert res["status"] == "ready"
