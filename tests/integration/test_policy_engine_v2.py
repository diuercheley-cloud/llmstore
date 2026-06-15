from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.policy_engine.base import DecisionResult, PolicyContext
from app.services.policy_engine.orchestrator import PolicyEngineOrchestrator


@pytest.fixture
def orchestrator():
    return PolicyEngineOrchestrator()


@pytest.mark.asyncio
async def test_builtin_allow_by_default(orchestrator):
    context = PolicyContext(tenant_id="tenant-1", action_type="inference", risk_score=0.1)

    decision = await orchestrator.evaluate(context, preferred_engine="builtin")

    assert decision.result == DecisionResult.ALLOW
    assert "default" in decision.reason.lower()


@pytest.mark.asyncio
async def test_builtin_deny_secret_access(orchestrator):
    context = PolicyContext(
        tenant_id="tenant-1", action_type="tool_call", data_classification="secret"
    )

    decision = await orchestrator.evaluate(context, preferred_engine="builtin")

    assert decision.result == DecisionResult.DENY
    assert "secret" in decision.reason.lower()


@pytest.mark.asyncio
async def test_builtin_require_approval_high_risk(orchestrator):
    context = PolicyContext(tenant_id="tenant-1", action_type="tool_call", risk_score=0.9)

    decision = await orchestrator.evaluate(context, preferred_engine="builtin")

    assert decision.result == DecisionResult.REQUIRE_APPROVAL
    assert "approval" in decision.reason.lower()


@pytest.mark.asyncio
async def test_fallback_to_builtin(orchestrator):
    # Simulate an engine that fails
    context = PolicyContext(tenant_id="tenant-1", action_type="tool_call", risk_score=0.9)

    # We'll mock one engine to raise an exception
    mock_engine = MagicMock()
    mock_engine.get_engine_name.return_value = "failing-engine"
    mock_engine.evaluate = AsyncMock(side_effect=Exception("Engine failure"))

    orchestrator.engines.append(mock_engine)

    decision = await orchestrator.evaluate(context, preferred_engine="failing-engine")

    # Should fallback to builtin which is REQUIRE_APPROVAL for risk 0.9
    assert decision.result == DecisionResult.REQUIRE_APPROVAL
    assert decision.engine == "builtin"


@pytest.mark.asyncio
async def test_evaluate_multi(orchestrator):
    context = PolicyContext(tenant_id="tenant-1", action_type="tool_call", risk_score=0.5)

    decisions = await orchestrator.evaluate_multi(context)

    assert len(decisions) >= 3  # builtin, opa, cedar
    assert any(d.engine == "builtin" for d in decisions)
    assert any(d.engine == "opa" for d in decisions)
    assert any(d.engine == "cedar" for d in decisions)
