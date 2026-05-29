import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.agents.multi_agent.team_observability import TeamObservability


@pytest.mark.asyncio
async def test_team_observability_records_message_and_trace():
    db = SimpleNamespace(add=Mock(), flush=AsyncMock())
    observability = TeamObservability(db)
    observability.record_trace = AsyncMock()

    run_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    recipient_id = uuid.uuid4()

    await observability.record_message(
        run_id,
        sender_id,
        recipient_id,
        "specialist result",
        "result",
    )

    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    observability.record_trace.assert_awaited_once()
