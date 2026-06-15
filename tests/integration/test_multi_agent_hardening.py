import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.config import get_settings
from app.services.agents.multi_agent.arbitration_engine import ArbitrationEngine
from app.services.agents.multi_agent.governance_policy import MultiAgentPolicyService
from app.services.agents.multi_agent.loop_guard import LoopGuard


@pytest.mark.asyncio
async def test_delegation_max_depth_policy():
    db = AsyncMock()
    policy = MultiAgentPolicyService(db)

    # Mocking a depth of 5
    policy._get_delegation_depth = AsyncMock(return_value=5)

    run_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    child_id = uuid.uuid4()

    allowed, reason = await policy.validate_delegation(run_id, parent_id, child_id)
    assert allowed is False
    assert "depth" in reason.lower()


@pytest.mark.asyncio
async def test_loop_guard_detection():
    db = AsyncMock()
    guard = LoopGuard(db)

    run_id = uuid.uuid4()
    p_id = uuid.uuid4()
    c_id = uuid.uuid4()

    # Mocking database result for cycle
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = MagicMock()
    db.execute = AsyncMock(return_value=res_mock)

    is_cycle = await guard.detect_cycle(run_id, p_id, c_id)
    assert is_cycle is True


@pytest.mark.asyncio
async def test_arbitration_engine_conflict_resolution():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = True

    engine = ArbitrationEngine()
    outputs = [
        {"agent_id": "a1", "result": "Yes", "confidence": 0.9},
        {"agent_id": "a2", "result": "No", "confidence": 0.8},
    ]

    res = await engine.arbitrate(outputs, {})
    assert res["status"] == "success"
    assert res["consensus"] is False
    assert "Synthesized Result" in res["final_synthesis"]
    assert "Yes" in res["final_synthesis"]


@pytest.mark.asyncio
async def test_arbitration_consensus():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = True

    engine = ArbitrationEngine()
    outputs = [
        {"agent_id": "a1", "result": "Same Answer", "confidence": 0.9},
        {"agent_id": "a2", "result": "Same Answer", "confidence": 0.8},
    ]

    res = await engine.arbitrate(outputs, {})
    assert res["consensus"] is True
    assert "Same Answer" in res["final_synthesis"]
