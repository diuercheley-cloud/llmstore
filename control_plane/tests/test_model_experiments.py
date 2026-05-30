import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.model_experiments.experiment_registry import ExperimentRegistry
from app.services.model_experiments.traffic_splitter import TrafficSplitter
from app.services.model_experiments.promotion_gate import PromotionGate

@pytest.mark.asyncio
async def test_traffic_split_90_10():
    session = AsyncMock()
    splitter = TrafficSplitter(session)
    
    # Mock experiments and variants
    experiment = MagicMock(id=uuid.uuid4(), status="running")
    variant_a = MagicMock(id=uuid.uuid4(), traffic_weight=90.0)
    variant_b = MagicMock(id=uuid.uuid4(), traffic_weight=10.0)
    
    # Mock database responses
    mock_res_exp = MagicMock()
    mock_res_exp.scalars.return_value.all.return_value = [experiment]
    
    mock_res_var = MagicMock()
    mock_res_var.scalars.return_value.all.return_value = [variant_a, variant_b]
    
    session.execute.side_effect = [mock_res_exp, mock_res_var]
    
    # Test random split (we mock random to force one branch)
    with patch("random.uniform", return_value=95.0):
        assigned = await splitter.get_assigned_variant("tenant-1")
        assert assigned == variant_b

@pytest.mark.asyncio
async def test_sticky_assignment():
    session = AsyncMock()
    splitter = TrafficSplitter(session)
    
    experiment_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    user_id = "user-1"
    
    # Mock existing assignment
    mock_res_exp = MagicMock()
    mock_res_exp.scalars.return_value.all.return_value = [MagicMock(id=experiment_id, status="running")]
    
    mock_res_assign = MagicMock()
    mock_res_assign.scalar_one_or_none.return_value = MagicMock(variant_id=variant_id)
    
    session.execute.side_effect = [mock_res_exp, mock_res_assign]
    session.get.return_value = MagicMock(id=variant_id)
    
    assigned = await splitter.get_assigned_variant("tenant-1", user_id=user_id)
    assert assigned.id == variant_id

@pytest.mark.asyncio
async def test_slo_breach_rollback():
    session = AsyncMock()
    gate = PromotionGate(session)
    
    experiment_id = uuid.uuid4()
    mock_exp = MagicMock(id=experiment_id, status="running")
    mock_exp.description = ""
    session.get.return_value = mock_exp
    
    await gate.rollback(experiment_id, "Latency SLO breached")
    
    assert mock_exp.status == "rolled_back"
    assert "Latency SLO breached" in mock_exp.description

@pytest.mark.asyncio
async def test_promotion_requires_variant():
    session = AsyncMock()
    gate = PromotionGate(session)
    
    experiment_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    mock_exp = MagicMock(id=experiment_id, status="running")
    session.get.return_value = mock_exp
    
    await gate.promote_variant(experiment_id, variant_id)
    assert mock_exp.status == "promoted"
