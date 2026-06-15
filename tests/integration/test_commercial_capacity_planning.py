from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.commercial.commercial_capacity import (
    CommercialCapacityForecast,
    CommercialCapacitySnapshot,
)
from app.services.routing.commercial_autoscaling import generate_autoscaling_recommendations
from app.services.routing.commercial_capacity_forecasting import forecast_capacity
from app.services.routing.commercial_capacity_monitor import (
    capture_capacity_snapshot,
    cleanup_old_snapshots,
)


@pytest.mark.asyncio
async def test_capture_capacity_snapshot_empty_data():
    db = AsyncMock()
    # Mock empty results for events and nodes
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_result

    with patch("app.services.routing.commercial_capacity_monitor.get_settings") as mock_settings:
        mock_settings.return_value.commercial_capacity_planning_enabled = True
        mock_settings.return_value.cluster_id = "test-cluster"
        mock_settings.return_value.commercial_node_offline_after_seconds = 120

        snapshots = await capture_capacity_snapshot(db)
        assert len(snapshots) == 0


@pytest.mark.asyncio
async def test_capture_capacity_snapshot_with_data():
    db = AsyncMock()

    # Mock results for events
    mock_events_result = MagicMock()
    mock_events_result.all.return_value = [
        ("deepseek", "deepseek-coder", "Premium", 100, 25.0, 5, 2, 0)
    ]

    # Mock results for nodes
    mock_node = MagicMock()
    mock_node.metadata_json = {
        "cpu_utilization": 45.0,
        "memory_utilization": 60.0,
        "gpu_utilization": 30.0,
    }
    mock_nodes_result = MagicMock()
    mock_nodes_result.scalars.return_value.all.return_value = [mock_node]

    db.execute.side_effect = [mock_events_result, mock_nodes_result]

    with patch("app.services.routing.commercial_capacity_monitor.get_settings") as mock_settings:
        mock_settings.return_value.commercial_capacity_planning_enabled = True
        mock_settings.return_value.cluster_id = "test-cluster"
        mock_settings.return_value.commercial_node_offline_after_seconds = 120

        snapshots = await capture_capacity_snapshot(db)
        assert len(snapshots) == 2  # 1 for provider/model + 1 for cluster global

        # Verify provider snapshot
        provider_snap = next(s for s in snapshots if s.provider == "deepseek")
        assert provider_snap.requests_per_minute == 100 / 5.0
        assert provider_snap.sla_violation_rate == 5.0

        # Verify cluster snapshot
        cluster_snap = next(s for s in snapshots if s.provider is None)
        assert cluster_snap.cpu_utilization == 45.0


@pytest.mark.asyncio
async def test_forecast_capacity_growth():
    db = AsyncMock()

    # Create 10 snapshots with increasing RPM
    snapshots = []
    base_time = datetime.now(UTC) - timedelta(hours=1)
    for i in range(10):
        snapshots.append(
            CommercialCapacitySnapshot(
                cluster_id="test-cluster",
                timestamp=base_time + timedelta(minutes=i * 5),
                requests_per_minute=10 + i * 2,  # Growing
                concurrent_requests=1,
                avg_latency_ms=100.0,
                sla_violation_rate=0.0,
            )
        )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = snapshots
    db.execute.return_value = mock_result

    with patch(
        "app.services.routing.commercial_capacity_forecasting.get_settings"
    ) as mock_settings:
        mock_settings.return_value.commercial_capacity_forecast_window_minutes = 60

        forecast = await forecast_capacity(db, "test-cluster")
        assert forecast is not None
        assert forecast.predicted_rpm > snapshots[-1].requests_per_minute
        assert forecast.recommended_action == "scale_up"


@pytest.mark.asyncio
async def test_generate_autoscaling_recommendations():
    db = AsyncMock()

    # Mock forecast with scale_up recommendation
    forecast = CommercialCapacityForecast(
        cluster_id="test-cluster",
        provider="deepseek",
        recommended_action="scale_up",
        confidence=0.9,
        predicted_rpm=50.0,
        predicted_sla_violation_rate=2.0,
    )

    # 1. Mock result for forecasts
    mock_forecast_result = MagicMock()
    mock_forecast_result.scalars.return_value.all.return_value = [forecast]

    # 2. Mock result for safety policy
    from app.models.commercial.commercial_infra_simulation import CommercialSafetyPolicy

    policy = CommercialSafetyPolicy(
        policy_name="default",
        enabled=True,
        max_predicted_cost_increase_percent=20.0,
        max_predicted_sla_violation_percent=5.0,
        require_manual_approval_above_blast_radius="medium",
    )
    mock_policy_result = MagicMock()
    mock_policy_result.scalar_one_or_none.return_value = policy

    db.execute.side_effect = [mock_forecast_result, mock_policy_result]

    with patch("app.services.routing.commercial_autoscaling.get_settings") as mock_settings:
        mock_settings.return_value.commercial_capacity_planning_enabled = True
        mock_settings.return_value.commercial_infra_simulation_enabled = True
        mock_settings.return_value.commercial_safety_gates_enabled = True
        mock_settings.return_value.commercial_sla_risk_alert_percent = 5.0

        recs = await generate_autoscaling_recommendations(db, "test-cluster")
        assert len(recs) == 1
        assert recs[0].recommendation_type == "scale_up"
        assert recs[0].target_identifier == "deepseek"


@pytest.mark.asyncio
async def test_cleanup_old_snapshots():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 10
    db.execute.return_value = mock_result

    with patch("app.services.routing.commercial_capacity_monitor.get_settings") as mock_settings:
        mock_settings.return_value.commercial_capacity_retention_days = 30

        deleted = await cleanup_old_snapshots(db)
        assert deleted == 10
