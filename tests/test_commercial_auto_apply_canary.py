import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commercial_routing_config import CommercialRoutingConfig
from app.services.routing.commercial_auto_apply import CommercialAutoApplyService
from app.services.routing.commercial_config_store import CommercialConfigStore

@pytest.fixture
def mock_db():
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.flush = AsyncMock()
    mock.refresh = AsyncMock()
    return mock

@pytest.fixture
def service(mock_db):
    return CommercialAutoApplyService(mock_db)

def setup_mock_count(mock_db, count: int):
    mock_result = MagicMock()
    mock_result.scalar.return_value = count
    mock_db.execute.return_value = mock_result

@pytest.mark.asyncio
async def test_evaluate_auto_apply_candidate_disabled(service, mock_db):
    service.settings.commercial_calibration_auto_apply = False
    recommendation = {"confidence": "high", "sample_count": 50, "cost_error_percent": 5.0}
    
    # Mock rate limit and recent data checks
    setup_mock_count(mock_db, 0) # For both checks
    
    res = await service.evaluate_auto_apply_candidate("openai", "gpt-4", recommendation)
    assert res["eligible"] is False
    assert "Auto-apply globally disabled" in res["reasons_rejected"]

@pytest.mark.asyncio
async def test_evaluate_auto_apply_candidate_low_confidence(service, mock_db):
    service.settings.commercial_calibration_auto_apply = True
    service.settings.commercial_calibration_auto_apply_min_confidence = "high"
    recommendation = {"confidence": "medium", "sample_count": 50, "cost_error_percent": 5.0}
    
    setup_mock_count(mock_db, 0)
    
    res = await service.evaluate_auto_apply_candidate("openai", "gpt-4", recommendation)
    assert res["eligible"] is False
    assert "Confidence medium is below required high" in res["reasons_rejected"]

@pytest.mark.asyncio
async def test_evaluate_auto_apply_candidate_large_change(service, mock_db):
    service.settings.commercial_calibration_auto_apply = True
    service.settings.commercial_calibration_auto_apply_max_change_percent = 10.0
    recommendation = {"confidence": "high", "sample_count": 50, "cost_error_percent": 15.0}
    
    setup_mock_count(mock_db, 0)
    
    res = await service.evaluate_auto_apply_candidate("openai", "gpt-4", recommendation)
    assert res["eligible"] is False
    assert "Recommended change 15.0% exceeds max 10.0%" in res["reasons_rejected"]

@pytest.mark.asyncio
async def test_evaluate_auto_apply_candidate_low_samples(service, mock_db):
    service.settings.commercial_calibration_auto_apply = True
    service.settings.commercial_calibration_auto_apply_min_recent_samples = 20
    recommendation = {"confidence": "high", "sample_count": 10, "cost_error_percent": 5.0}
    
    setup_mock_count(mock_db, 0)
    
    res = await service.evaluate_auto_apply_candidate("openai", "gpt-4", recommendation)
    assert res["eligible"] is False
    assert "Sample count 10 below minimum 20" in res["reasons_rejected"]

@pytest.mark.asyncio
async def test_evaluate_auto_apply_candidate_no_recent_data(service, mock_db):
    service.settings.commercial_calibration_auto_apply = True
    service.settings.commercial_calibration_auto_apply_require_24h_data = True
    recommendation = {"confidence": "high", "sample_count": 50, "cost_error_percent": 5.0}
    
    # First call to has_recent_data will execute count query
    # Second call to is_rate_limited will also execute count query
    # Since they use the same mock_db, we need to be careful or use side_effect
    mock_result_no_recent = MagicMock()
    mock_result_no_recent.scalar.return_value = 0
    mock_db.execute.return_value = mock_result_no_recent
    
    res = await service.evaluate_auto_apply_candidate("openai", "gpt-4", recommendation)
    assert res["eligible"] is False
    assert "No data in the last 24 hours" in res["reasons_rejected"]

@pytest.mark.asyncio
async def test_evaluate_auto_apply_candidate_eligible(service, mock_db):
    service.settings.commercial_calibration_auto_apply = True
    service.settings.commercial_calibration_auto_apply_min_confidence = "high"
    service.settings.commercial_calibration_auto_apply_max_change_percent = 10.0
    service.settings.commercial_calibration_auto_apply_min_recent_samples = 20
    recommendation = {
        "confidence": "high", 
        "sample_count": 50, 
        "cost_error_percent": 5.0,
        "recommended_multiplier": 1.05
    }
    
    mock_result_ok = MagicMock()
    mock_result_ok.scalar.return_value = 5 # count > 0 for recent data
    
    # We need recent data = True AND rate limited = False
    # is_rate_limited also uses count. If count=0 it's not rate limited.
    # This is tricky with a single mock for multiple calls.
    
    with patch.object(service, "has_recent_data", new_callable=AsyncMock) as mock_recent:
        mock_recent.return_value = True
        with patch.object(service, "is_rate_limited", new_callable=AsyncMock) as mock_rl:
            mock_rl.return_value = False
            res = await service.evaluate_auto_apply_candidate("openai", "gpt-4", recommendation)
            assert res["eligible"] is True
            assert len(res["reasons_rejected"]) == 0

def test_get_canary_bucket_consistency():
    req_id = "test-req-123"
    bucket1 = CommercialAutoApplyService.get_canary_bucket(req_id, None, None)
    bucket2 = CommercialAutoApplyService.get_canary_bucket(req_id, None, None)
    assert bucket1 == bucket2
    assert 0 <= bucket1 < 100

def test_get_canary_bucket_distribution():
    buckets = []
    for i in range(1000):
        buckets.append(CommercialAutoApplyService.get_canary_bucket(str(uuid.uuid4()), None, None))
    
    # 5% canary should catch about 50 in 1000 samples
    canary_count = len([b for b in buckets if b < 5])
    assert 30 < canary_count < 70 # Very loose check for distribution

@pytest.mark.asyncio
async def test_apply_canary_config(service, mock_db):
    service.settings.commercial_calibration_canary_default_percent = 5
    eval_result = {
        "recommended_multiplier": 1.05,
        "confidence": "high",
        "sample_count": 50,
        "change_percent": 5.0
    }
    
    # Mock store.get_effective_config
    service.store.get_effective_config = AsyncMock(return_value={
        "margin_weight": 0.6,
        "latency_weight": 0.2,
        "quality_weight": 0.2,
        "local_route_bonus": 20.0,
        "min_margin_percent": 10.0
    })
    
    config = await service.apply_canary_config("openai", "gpt-4", eval_result)
    
    assert config.canary_enabled is True
    assert config.canary_percent == 5
    assert config.cost_multiplier == 1.05
    assert config.auto_applied is True
    assert config.provider == "openai"
    assert config.model == "gpt-4"
    mock_db.add.assert_called()

@pytest.mark.asyncio
async def test_promote_canary(service, mock_db):
    config_id = uuid.uuid4()
    canary = CommercialRoutingConfig(
        id=config_id,
        canary_enabled=True,
        canary_percent=5,
        provider="openai",
        model="gpt-4",
        is_active=True,
        scope_type="provider_model"
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = canary
    mock_db.execute.return_value = mock_result
    
    promoted = await service.promote_canary(config_id)
    
    assert promoted.canary_enabled is False
    assert promoted.canary_percent == 0
    assert promoted.is_active is True

@pytest.mark.asyncio
async def test_rollback_canary(service, mock_db):
    config_id = uuid.uuid4()
    canary = CommercialRoutingConfig(id=config_id, is_active=True)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = canary
    mock_db.execute.return_value = mock_result
    
    success = await service.rollback_canary(config_id)
    assert success is True
    assert canary.is_active is False
