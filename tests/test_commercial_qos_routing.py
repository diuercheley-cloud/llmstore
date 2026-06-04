from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.commercial_qos_tier import CommercialQoSTier
from app.services.routing.commercial_qos import CommercialQoSService


@pytest.mark.asyncio
async def test_resolve_qos_tier_by_plan():
    db = MagicMock()
    # Mock result for select(CommercialQoSTier).where(CommercialQoSTier.name == "Enterprise")
    enterprise_tier = CommercialQoSTier(name="Enterprise", priority=1000)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = enterprise_tier
    db.execute = AsyncMock(return_value=mock_result)
    
    tier = await CommercialQoSService.resolve_qos_tier(db, None, "enterprise")
    assert tier.name == "Enterprise"
    assert tier.priority == 1000

def test_evaluate_route_against_qos_free_blocks_cloud():
    tier = CommercialQoSTier(
        name="Free",
        allow_cloud=False,
        min_margin_percent=20.0,
        max_cost_per_request_brl=0.01
    )
    
    # Cloud candidate
    candidate = {"provider": "openai", "quality": 90}
    is_pass, reasons = CommercialQoSService.evaluate_route_against_qos(
        tier, candidate, estimated_margin_percent=25.0, estimated_cost_brl=0.005, is_cloud=True
    )
    assert is_pass is False
    assert "cloud_not_allowed_for_tier" in reasons

def test_evaluate_route_against_qos_premium_allows_cloud():
    tier = CommercialQoSTier(
        name="Premium",
        allow_cloud=True,
        min_margin_percent=5.0,
        max_cost_per_request_brl=1.0
    )
    
    # Cloud candidate
    candidate = {"provider": "openai", "quality": 90}
    is_pass, reasons = CommercialQoSService.evaluate_route_against_qos(
        tier, candidate, estimated_margin_percent=10.0, estimated_cost_brl=0.05, is_cloud=True
    )
    assert is_pass is True
    assert len(reasons) == 0

def test_evaluate_route_against_qos_latency_violation():
    tier = CommercialQoSTier(
        name="Enterprise",
        max_p95_latency_ms=400
    )
    
    candidate = {"provider": "local", "quality": 70}
    is_pass, reasons = CommercialQoSService.evaluate_route_against_qos(
        tier, candidate, estimated_margin_percent=None, estimated_cost_brl=0.0, is_cloud=False, current_p95_latency=500
    )
    assert is_pass is False
    assert any("latency_p95" in r for r in reasons)

def test_choose_degradation_path_best_effort():
    tier = CommercialQoSTier(name="Free", degradation_policy="best_effort")
    candidates = []
    rejected = [MagicMock(estimated_cost_brl=0.01)]
    
    selected, path = CommercialQoSService.choose_degradation_path(tier, candidates, rejected)
    assert selected == rejected[0]
    assert path == "best_effort_fallback"

def test_choose_degradation_path_block():
    tier = CommercialQoSTier(name="Strict", degradation_policy="block")
    candidates = []
    rejected = [MagicMock()]
    
    selected, path = CommercialQoSService.choose_degradation_path(tier, candidates, rejected)
    assert selected is None
    assert path == "blocked_by_policy"
