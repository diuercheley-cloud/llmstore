import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.agents.continuous_promotion import ContinuousPromotionService
from app.services.agents.rollback_controller import RollbackController

@pytest.mark.asyncio
async def test_promotion_confidence_threshold():
    db = AsyncMock()
    service = ContinuousPromotionService(db)
    
    agent_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    
    # Below threshold (0.85)
    res = await service.create_promotion_candidate(agent_id, candidate_id, 0.70)
    assert res["status"] == "rejected"
    assert "below threshold" in res["reason"]
    
    # Above threshold
    res = await service.create_promotion_candidate(agent_id, candidate_id, 0.90)
    assert res["status"] == "initiated"

@pytest.mark.asyncio
async def test_auto_rollback_on_latency_breach():
    db = AsyncMock()
    controller = RollbackController(db)
    agent_id = uuid.uuid4()
    
    baseline = {"avg_latency_ms": 1000, "success_rate": 0.99}
    breach = {"avg_latency_ms": 1600, "success_rate": 0.99} # > 50% increase
    
    # Trigger rollback
    controller.trigger_rollback = AsyncMock(return_value=True)
    
    should_rollback = await controller.monitor_slo_breach(agent_id, breach, baseline)
    assert should_rollback is True
    controller.trigger_rollback.assert_called_once()

@pytest.mark.asyncio
async def test_production_requires_approval():
    db = AsyncMock()
    service = ContinuousPromotionService(db)
    agent_id = uuid.uuid4()
    
    # No approval provided
    with pytest.raises(ValueError, match="Human approval is required"):
        await service.promote_to_production(agent_id, approved_by=None)
        
    # Valid approval
    res = await service.promote_to_production(agent_id, approved_by="admin-1")
    assert res is True
