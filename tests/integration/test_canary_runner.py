import uuid
from unittest.mock import AsyncMock

import pytest
from app.services.agents.canary_runner import CanaryRunner


@pytest.mark.asyncio
async def test_canary_runner_routes_to_candidate_when_bucket_is_within_weight(monkeypatch):
    runner = CanaryRunner(AsyncMock())
    candidate_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    monkeypatch.setattr(runner, "_stable_bucket", lambda *_args: 3)

    selected = await runner.decide_definition(
        agent_id,
        "tenant-a",
        [{"id": candidate_id, "traffic_weight": 5}],
    )

    assert selected == candidate_id


@pytest.mark.asyncio
async def test_canary_runner_falls_back_to_production_when_bucket_exceeds_weight(monkeypatch):
    runner = CanaryRunner(AsyncMock())
    agent_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    monkeypatch.setattr(runner, "_stable_bucket", lambda *_args: 80)

    selected = await runner.decide_definition(
        agent_id,
        "tenant-a",
        [{"id": candidate_id, "traffic_weight": 5}],
    )

    assert selected == agent_id
