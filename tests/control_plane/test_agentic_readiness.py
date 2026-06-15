import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agent_execution import AgentWorkerHeartbeat
from app.models.agents.agents import AgentIncident
from app.services.agents.agent_readiness import AgentReadinessService


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents.agents  # noqa

        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_readiness_degraded_worker_down():
    async with SessionLocal() as db:
        from app.core.config import get_settings

        settings = get_settings()
        settings.agent_runtime_enabled = True
        # No heartbeats -> degraded (active_workers = 0)
        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert res["status"] == "degraded"
        assert res["checks"]["active_workers"]["status"] == "warn"


@pytest.mark.asyncio
async def test_readiness_unhealthy_critical_incident():
    async with SessionLocal() as db:
        from app.core.config import get_settings

        settings = get_settings()
        settings.agent_runtime_enabled = True
        # Create critical incident
        inc = AgentIncident(
            tenant_id="t1",
            agent_id=uuid.uuid4(),
            incident_type="memory_isolation_violation",
            title="CRITICAL",
            severity="critical",
            status="open",
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
        hb = AgentWorkerHeartbeat(worker_id="w1", last_heartbeat=datetime.now(UTC))
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


@pytest.mark.asyncio
async def test_readiness_dlq_zero():
    async with SessionLocal() as db:
        from app.core.config import get_settings

        settings = get_settings()
        settings.agent_runtime_enabled = True

        hb = AgentWorkerHeartbeat(worker_id="w-dlq-test", last_heartbeat=datetime.now(UTC))
        db.add(hb)
        await db.commit()

        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert "dead_letter_queue" in res["checks"]
        assert res["checks"]["dead_letter_queue"]["value"] == 0
        assert res["checks"]["dead_letter_queue"]["status"] == "pass"


@pytest.mark.asyncio
async def test_readiness_retry_backlog():
    async with SessionLocal() as db:
        from app.core.config import get_settings
        from app.models.agents.agent_execution import AgentExecutionRetry

        settings = get_settings()
        settings.agent_runtime_enabled = True

        # Add retry records with future next_attempt_at
        for i in range(15):
            retry = AgentExecutionRetry(
                job_id=uuid.uuid4(),
                attempt=1,
                error_message="test",
                attempted_at=datetime.now(UTC),
                next_attempt_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            db.add(retry)
        await db.commit()

        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert res["checks"]["retry_backlog"]["value"] >= 10
        assert res["checks"]["retry_backlog"]["status"] == "warn"


@pytest.mark.asyncio
async def test_compose_config_has_agent_worker():
    """
    Validates that docker-compose.yml contains the agent-worker service.
    This is a static validation that the compose configuration is correct.
    """
    import os

    import yaml

    compose_path = os.path.join(os.path.dirname(__file__), "../../docker-compose.yml")
    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    assert "services" in compose
    assert "agent-worker" in compose["services"]
    aw = compose["services"]["agent-worker"]
    assert "agentic" in aw.get("profiles", [])
    assert "AGENT_WORKER_ENABLED" in str(aw.get("environment", {}))


@pytest.mark.asyncio
async def test_readiness_degraded_when_worker_enabled_but_no_heartbeat():
    async with SessionLocal() as db:
        from app.core.config import get_settings

        settings = get_settings()
        settings.agent_runtime_enabled = True

        # No heartbeat at all
        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert res["checks"]["active_workers"]["status"] == "warn"
        # Should be degraded rather than ready because no workers
        assert res["status"] in ("degraded",)


@pytest.mark.asyncio
async def test_readiness_ok_with_heartbeat_mock():
    async with SessionLocal() as db:
        from app.core.config import get_settings

        settings = get_settings()
        settings.agent_runtime_enabled = True

        hb = AgentWorkerHeartbeat(
            worker_id="w-healthy",
            last_heartbeat=datetime.now(UTC),
            status="active",
        )
        db.add(hb)
        await db.commit()

        svc = AgentReadinessService(db)
        res = await svc.check_readiness()
        assert res["checks"]["active_workers"]["status"] == "pass"
        assert res["status"] == "ready"


@pytest.mark.asyncio
async def test_embedded_worker_off_by_default():
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.agent_embedded_worker_enabled is False


@pytest.mark.asyncio
async def test_queue_inspect_script_syntax():
    import subprocess

    result = subprocess.run(
        ["bash", "-n", "scripts/dev/agent-queue-inspect.sh"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Syntax error: {result.stderr}"
