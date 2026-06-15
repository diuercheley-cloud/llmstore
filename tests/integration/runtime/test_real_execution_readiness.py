import pytest
from app.services.runtime.real_execution_readiness import (
    RealExecutionReadinessService,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_readiness_production_blocked_by_mock(session: AsyncSession, settings):
    settings.deployment_mode = "production"
    settings.agent_executor_mock_mode = True  # This should block

    svc = RealExecutionReadinessService(session)
    results = await svc.check_readiness()

    assert results["status"] == "production_blocked"
    assert any("Mock execution mode" in b for b in results["blockers"])


@pytest.mark.asyncio
async def test_readiness_production_blocked_by_disabled_queue(session: AsyncSession, settings):
    settings.deployment_mode = "production"
    settings.agent_execution_plane_enabled = False  # Required for production

    svc = RealExecutionReadinessService(session)
    results = await svc.check_readiness()

    assert results["status"] == "production_blocked"
    assert any("Durable execution queue is disabled" in b for b in results["blockers"])


@pytest.mark.asyncio
async def test_readiness_pilot_ready_with_warnings(session: AsyncSession, settings):
    settings.deployment_mode = "pilot"
    settings.agent_execution_plane_enabled = True  # Avoid blocking pilot by queue
    settings.agent_execution_enabled = False  # Generates warning but not blocker for pilot
    settings.agent_executor_mock_mode = (
        False  # Must disable mock mode so it falls through to exec_enabled check
    )

    svc = RealExecutionReadinessService(session)
    results = await svc.check_readiness()

    assert results["status"] == "pilot_ready"
    assert any("Real tool execution is disabled" in w for w in results["warnings"])


@pytest.mark.asyncio
async def test_readiness_dev_ready_by_default(session: AsyncSession, settings):
    settings.deployment_mode = "appliance"
    settings.agent_execution_plane_enabled = False  # fine for dev
    settings.agent_execution_enabled = False

    svc = RealExecutionReadinessService(session)
    results = await svc.check_readiness()

    # In dev mode, missing real execution is fine
    assert results["status"] == "dev_ready"
