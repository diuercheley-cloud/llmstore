import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.agents.multi_agent.specialist_routing_runtime import SpecialistRoutingRuntime


@pytest.mark.asyncio
async def test_specialist_routing_runtime_executes_dispatch_and_synthesis():
    runtime = SpecialistRoutingRuntime(AsyncMock())
    team_id = uuid.uuid4()
    run_id = uuid.uuid4()
    dispatcher_id = uuid.uuid4()
    specialist_id = uuid.uuid4()

    runtime.get_team = AsyncMock(return_value=SimpleNamespace(tenant_id="tenant-a"))
    runtime.get_members = AsyncMock(
        return_value=[
            SimpleNamespace(role="dispatcher", agent_id=dispatcher_id),
            SimpleNamespace(role="specialist", agent_id=specialist_id),
        ]
    )
    runtime.start_run = AsyncMock(return_value=SimpleNamespace(id=run_id))
    runtime.get_workspace = lambda _tenant_id: SimpleNamespace()
    runtime.complete_run = AsyncMock()
    runtime.fail_run = AsyncMock()
    runtime.obs.record_trace = AsyncMock()
    runtime.obs.record_message = AsyncMock()
    runtime.policy.validate_delegation = AsyncMock(return_value=(True, "OK"))
    runtime.arbitrator.arbitrate = AsyncMock(
        return_value={"final_synthesis": "final answer"}
    )

    result = await runtime.execute(team_id, "investigate auth regression")

    assert result == "final answer"
    runtime.arbitrator.arbitrate.assert_awaited_once()
    runtime.complete_run.assert_awaited_once_with(run_id, "final answer")
    runtime.fail_run.assert_not_awaited()
