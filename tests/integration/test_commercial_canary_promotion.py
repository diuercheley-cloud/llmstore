import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.commercial.commercial_routing_config import CommercialRoutingConfig
from app.services.routing.commercial_canary_promotion import CommercialCanaryPromotionService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    mock = MagicMock(spec=AsyncSession)
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.flush = AsyncMock()
    mock.get = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture
def service(mock_db):
    return CommercialCanaryPromotionService(mock_db)


@pytest.mark.asyncio
async def test_evaluate_canary_slo_not_found(service, mock_db):
    mock_db.get.return_value = None
    res = await service.evaluate_canary_slo(uuid.uuid4())
    assert res["pass"] is False
    assert "Config not found" in res["reason"]


@pytest.mark.asyncio
async def test_evaluate_canary_slo_pass(service, mock_db):
    config_id = uuid.uuid4()
    config = CommercialRoutingConfig(
        id=config_id,
        canary_enabled=True,
        canary_percent=5,
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    mock_db.get.return_value = config

    # Mock metrics query
    mock_metrics = MagicMock()
    mock_metrics.total = 150
    mock_metrics.errors = 1
    mock_metrics.avg_latency = 100
    mock_metrics.p95_latency = 150
    mock_metrics.avg_margin = 25.0
    mock_metrics.avg_est_error = 5.0
    mock_metrics.fallbacks = 0
    mock_metrics.blocks = 0

    mock_res = MagicMock()
    mock_res.one.return_value = mock_metrics
    mock_db.execute.return_value = mock_res

    res = await service.evaluate_canary_slo(config_id)
    assert res["pass"] is True
    assert all(c["pass"] for c in res["checks"])


@pytest.mark.asyncio
async def test_evaluate_canary_slo_fail_low_requests(service, mock_db):
    config_id = uuid.uuid4()
    config = CommercialRoutingConfig(
        id=config_id,
        canary_enabled=True,
        canary_percent=5,
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    mock_db.get.return_value = config

    # Mock metrics query with few requests
    mock_metrics = MagicMock()
    mock_metrics.total = 10  # Below 100
    mock_metrics.errors = 0
    mock_metrics.avg_latency = 100
    mock_metrics.avg_margin = 25.0
    mock_metrics.avg_est_error = 5.0
    mock_metrics.fallbacks = 0
    mock_metrics.blocks = 0

    mock_res = MagicMock()
    mock_res.one.return_value = mock_metrics
    mock_db.execute.return_value = mock_res

    res = await service.evaluate_canary_slo(config_id)
    assert res["pass"] is False
    assert any(c["name"] == "min_requests" and not c["pass"] for c in res["checks"])


@pytest.mark.asyncio
async def test_promote_canary_step_dry_run(service, mock_db):
    config_id = uuid.uuid4()
    config = CommercialRoutingConfig(
        id=config_id,
        canary_enabled=True,
        canary_percent=5,
        canary_started_at=datetime.now(UTC) - timedelta(hours=2),
    )
    mock_db.get.return_value = config
    service.settings.commercial_canary_auto_promotion_mode = "dry_run"

    # Mock SLO pass
    with patch.object(
        CommercialCanaryPromotionService,
        "evaluate_canary_slo",
        return_value={"pass": True, "metrics": {"canary": {"request_count": 150}}},
    ):
        res = await service.promote_canary_step(config_id)
        assert res["action"] == "promote"
        assert res["mode"] == "dry_run"
        assert res["would_promote_to"] == 10
        assert config.canary_percent == 5  # Unchanged


@pytest.mark.asyncio
async def test_promote_canary_step_promote(service, mock_db):
    config_id = uuid.uuid4()
    config = CommercialRoutingConfig(
        id=config_id,
        canary_enabled=True,
        canary_percent=5,
        canary_started_at=datetime.now(UTC) - timedelta(hours=2),
    )
    mock_db.get.return_value = config
    service.settings.commercial_canary_auto_promotion_mode = "promote"

    # Mock SLO pass
    with patch.object(
        CommercialCanaryPromotionService,
        "evaluate_canary_slo",
        return_value={"pass": True, "metrics": {"canary": {"request_count": 150}}},
    ):
        res = await service.promote_canary_step(config_id)
        assert res["action"] == "promoted"
        assert res["new_percent"] == 10
        assert config.canary_percent == 10


@pytest.mark.asyncio
async def test_complete_canary_to_stable(service, mock_db):
    config_id = uuid.uuid4()
    config = CommercialRoutingConfig(
        id=config_id, canary_enabled=True, canary_percent=50, scope_type="global"
    )
    mock_db.get.return_value = config
    service.settings.commercial_canary_promotion_steps = "5,10,25,50"  # Current is last step
    service.settings.commercial_canary_auto_promotion_mode = "promote"

    with patch.object(
        CommercialCanaryPromotionService,
        "evaluate_canary_slo",
        return_value={"pass": True, "metrics": {"canary": {"request_count": 150}}},
    ):
        res = await service.promote_canary_step(config_id)
        assert res["action"] == "completed"
        assert config.canary_enabled is False
        assert config.canary_promotion_status == "completed"


@pytest.mark.asyncio
async def test_auto_rollback_critical_error(service, mock_db):
    config_id = uuid.uuid4()
    config = CommercialRoutingConfig(id=config_id, canary_enabled=True, is_active=True)
    mock_db.get.return_value = config

    # Mock critical error rate
    mock_metrics = MagicMock()
    mock_metrics.total = 100
    mock_metrics.errors = 15  # 15% > 10% critical
    mock_metrics.avg_latency = 100
    mock_metrics.avg_margin = 25.0
    mock_metrics.avg_est_error = 5.0
    mock_metrics.fallbacks = 0
    mock_metrics.blocks = 0

    mock_res = MagicMock()
    mock_res.one.return_value = mock_metrics
    mock_db.execute.return_value = mock_res

    res = await service.auto_rollback_if_unhealthy(config_id)
    assert res["action"] == "rolled_back"
    assert config.is_active is False
    assert config.canary_promotion_status == "rolled_back"
