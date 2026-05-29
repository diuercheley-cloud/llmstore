import pytest
import pytest_asyncio
import uuid
import json
from unittest.mock import patch, MagicMock

from app.core.config import get_settings
from app.services.agents.multi_agent.arbitration_engine import (
    ArbitrationEngine,
    ArbitrationExecutionError,
    CandidateResponse,
    CriticReview,
    ArbitrationDecision,
    ArbitrationCase
)
from app.services.agents.agent_llm_provider import ProviderResponse

@pytest.mark.asyncio
async def test_conflict_between_2_agents_creates_arbitration_case():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = True

    engine = ArbitrationEngine()
    candidates = [
        CandidateResponse(
            agent_id="agent-1",
            content="Use approach A for DB optimization",
            evidence="Performance tests show 20% speedup",
            confidence=0.9
        ),
        CandidateResponse(
            agent_id="agent-2",
            content="Use approach B for DB optimization",
            evidence="Security audit approved",
            confidence=0.8
        )
    ]

    res = await engine.arbitrate(candidates, {"goal": "Optimize database"})

    assert res["status"] == "success"
    assert res["consensus"] is False
    assert "decision" in res
    assert res["decision"]["winner_id"] == "agent-1" # Higher confidence and evidence
    assert len(res["decision"]["conflicts_unresolved"]) > 0
    assert "Conflict between agent-1 and agent-2" in res["decision"]["conflicts_unresolved"][0]

@pytest.mark.asyncio
async def test_critic_review_via_mock_llm_provider():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_critic_review_enabled = True
    settings.agent_multi_agent_mock_arbitration = False

    # Create a mock LLM provider return payload
    mock_response_json = {
        "correctness": 0.95,
        "completeness": 0.90,
        "tool_evidence": 0.85,
        "policy_compliance": 1.0,
        "cost": 0.95,
        "latency": 0.90,
        "confidence": 0.90,
        "safety": 1.0,
        "reasoning": "Strong evidence and correct implementation logic.",
        "recommendation": "approve"
    }

    mock_resp = ProviderResponse(
        type="final",
        output=json.dumps(mock_response_json)
    )

    mock_provider = MagicMock()
    from unittest.mock import AsyncMock
    mock_provider.generate = AsyncMock(return_value=mock_resp)

    with patch("app.services.agents.multi_agent.arbitration_engine.get_agent_llm_provider", return_value=mock_provider):
        engine = ArbitrationEngine()
        candidates = [
            CandidateResponse(
                agent_id="agent-1",
                content="Optimized query",
                evidence="Executed EXPLAIN ANALYZE",
                confidence=0.9
            )
        ]

        res = await engine.arbitrate(candidates, {
            "goal": "Optimize query",
            "critics": ["critic-1"],
            "tenant_id": "test-tenant"
        })

        assert res["status"] == "success"
        assert len(res["case"]["critic_reviews"]) == 1
        assert res["case"]["critic_reviews"][0]["reviewer_id"] == "critic-1"
        assert res["case"]["critic_reviews"][0]["correctness"] == 0.95
        assert res["case"]["critic_reviews"][0]["reasoning"] == "Strong evidence and correct implementation logic."

@pytest.mark.asyncio
async def test_heuristic_only_disabled_in_production():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = False
    settings.agent_multi_agent_mock_arbitration = False

    engine = ArbitrationEngine()
    candidates = [
        CandidateResponse(agent_id="a1", content="res")
    ]

    with pytest.raises(PermissionError) as exc_info:
        await engine.arbitrate(candidates, {"goal": "test"})
    assert "Multi-agent arbitration is disabled by feature flag" in str(exc_info.value)


@pytest.mark.asyncio
async def test_real_arbitration_requires_critic_review_flag():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = False
    settings.agent_multi_agent_critic_review_enabled = False

    engine = ArbitrationEngine()
    with pytest.raises(ArbitrationExecutionError, match="requires AGENT_MULTI_AGENT_CRITIC_REVIEW_ENABLED=true"):
        await engine.arbitrate([CandidateResponse(agent_id="a1", content="res")], {"goal": "test"})


@pytest.mark.asyncio
async def test_real_arbitration_blocks_silent_fallback_on_llm_error():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = False
    settings.agent_multi_agent_critic_review_enabled = True

    mock_provider = MagicMock()
    from unittest.mock import AsyncMock
    mock_provider.generate = AsyncMock(side_effect=RuntimeError("provider down"))

    with patch("app.services.agents.multi_agent.arbitration_engine.get_agent_llm_provider", return_value=mock_provider):
        engine = ArbitrationEngine()
        with pytest.raises(ArbitrationExecutionError, match="silent heuristic fallback is blocked"):
            await engine.arbitrate(
                [CandidateResponse(agent_id="agent-1", content="Optimized query", evidence="Executed EXPLAIN ANALYZE", confidence=0.9)],
                {"goal": "Optimize query", "critics": ["critic-1"], "tenant_id": "test-tenant"},
            )

@pytest.mark.asyncio
async def test_safety_failure_loses():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = True

    engine = ArbitrationEngine()
    candidates = [
        CandidateResponse(
            agent_id="unsafe-agent",
            content="Expose private database password",
            evidence="None",
            confidence=0.99, # Very high confidence
            safety_passed=False # Unsafe
        ),
        CandidateResponse(
            agent_id="safe-agent",
            content="Keep passwords in KMS vault",
            evidence="KMS integration configured",
            confidence=0.8,
            safety_passed=True
        )
    ]

    res = await engine.arbitrate(candidates, {"goal": "Handle passwords"})
    assert res["status"] == "success"
    assert res["decision"]["winner_id"] == "safe-agent"
    assert res["decision"]["scores"]["unsafe-agent"] == 0.0 # Safety failure sets final score to 0.0

@pytest.mark.asyncio
async def test_output_without_evidence_loses():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = True

    engine = ArbitrationEngine()
    candidates = [
        CandidateResponse(
            agent_id="spec-with-evidence",
            content="Recommendation A",
            evidence="Executed query showing latency is 10ms",
            confidence=0.8
        ),
        CandidateResponse(
            agent_id="spec-without-evidence",
            content="Recommendation B",
            evidence="", # Missing evidence
            confidence=0.95
        )
    ]

    res = await engine.arbitrate(candidates, {"goal": "Get metrics"})
    assert res["status"] == "success"
    assert res["decision"]["winner_id"] == "spec-with-evidence"
    assert res["decision"]["scores"]["spec-without-evidence"] == 0.0 # Lack of evidence sets final score to 0.0 when competing with evidence

@pytest.mark.asyncio
async def test_final_decision_has_receipt():
    settings = get_settings()
    settings.agent_multi_agent_arbitration_enabled = True
    settings.agent_multi_agent_mock_arbitration = True

    engine = ArbitrationEngine()
    candidates = [
        CandidateResponse(
            agent_id="agent-1",
            content="Simple text response",
            confidence=0.8
        )
    ]

    res = await engine.arbitrate(candidates, {"goal": "Check system status"})
    
    assert res["status"] == "success"
    assert "receipt" in res
    assert "receipt_id" in res["receipt"]
    assert res["receipt"]["winner_id"] == "agent-1"
    assert res["receipt"]["highest_score"] > 0.0
    assert "timestamp" in res["receipt"]
