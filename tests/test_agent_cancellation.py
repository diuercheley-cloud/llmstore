import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.agents.agent_cancellation import AgentCancellationService


@pytest.mark.asyncio
async def test_agent_cancellation_cancel_run_updates_run_without_job(monkeypatch):
    run_id = uuid.uuid4()
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)

    monkeypatch.setattr(
        "app.services.agents.agent_cancellation.agent_state.get_agent_run",
        AsyncMock(return_value=SimpleNamespace(status="running")),
    )
    update_run = AsyncMock()
    log_run_event = AsyncMock()
    monkeypatch.setattr("app.services.agents.agent_cancellation.agent_state.update_run", update_run)
    monkeypatch.setattr("app.services.agents.agent_cancellation.agent_state.log_run_event", log_run_event)

    result = await AgentCancellationService.cancel_run(db, run_id)

    assert result is True
    update_run.assert_awaited_once()
    log_run_event.assert_awaited_once()
    db.commit.assert_awaited_once()
