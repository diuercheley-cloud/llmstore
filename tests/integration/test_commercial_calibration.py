import uuid
from datetime import UTC, datetime

import pytest
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from app.services.routing import commercial_calibration


@pytest.mark.asyncio
async def test_calculate_estimation_error_no_data(session):
    """
    Should return low confidence when no data is available.
    """
    result = await commercial_calibration.calculate_estimation_error(session, min_samples=10)
    assert result["confidence"] == "low"
    assert "Insufficient data" in result["reason"]


@pytest.mark.asyncio
async def test_calculate_estimation_error_with_data(session):
    """
    Should calculate error correctly when data is present.
    """
    # Create fake events
    for _ in range(5):
        event = CommercialRoutingEvent(
            id=uuid.uuid4(),
            selected_provider="openai",
            selected_model="gpt-4",
            estimated_cost_brl=1.0,
            actual_cost_brl=1.2,  # 20% error (underestimated)
            actual_revenue_brl=2.0,
            created_at=datetime.now(UTC),
        )
        session.add(event)

    await session.commit()

    result = await commercial_calibration.calculate_estimation_error(
        session, provider="openai", model="gpt-4", min_samples=5
    )

    assert result["sample_count"] == 5
    assert result["avg_estimated_cost"] == 1.0
    assert result["avg_actual_cost"] == 1.2
    assert result["cost_error_percent"] == -16.67  # (1.0 - 1.2) / 1.2 * 100 = -16.666...
    assert result["confidence"] in ["medium", "high"]


def test_recommend_cost_multiplier():
    """
    Should recommend correct multipliers.
    """
    # Case 1: Underestimated (error is negative)
    # est = 1.0, act = 1.2, error_pct = -16.67
    # mult = 1 / (1 - 0.1667) = 1 / 0.8333 = 1.2
    mult = commercial_calibration.recommend_cost_multiplier(-16.67, "high")
    assert round(mult, 2) == 1.20

    # Case 2: Overestimated (error is positive)
    # est = 1.2, act = 1.0, error_pct = 20
    # mult = 1 / (1 + 0.2) = 1 / 1.2 = 0.833
    mult = commercial_calibration.recommend_cost_multiplier(20.0, "high")
    assert round(mult, 2) == 0.83

    # Case 3: Caps
    mult = commercial_calibration.recommend_cost_multiplier(-90.0, "high")
    assert mult <= 3.0  # Max default

    mult = commercial_calibration.recommend_cost_multiplier(200.0, "high")
    assert mult >= 0.5  # Min default


@pytest.mark.asyncio
async def test_generate_calibration_report(session):
    """
    Should generate a comprehensive report.
    """
    # Create fake events for different providers
    session.add(
        CommercialRoutingEvent(
            selected_provider="openai",
            selected_model="gpt-4",
            estimated_cost_brl=1.0,
            actual_cost_brl=1.5,  # 50% under
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        CommercialRoutingEvent(
            selected_provider="anthropic",
            selected_model="claude-3",
            estimated_cost_brl=1.5,
            actual_cost_brl=1.0,  # 50% over
            created_at=datetime.now(UTC),
        )
    )
    await session.commit()

    report = await commercial_calibration.generate_calibration_report(session, min_samples=1)

    assert "global_error_summary" in report
    assert len(report["recommended_cost_multipliers"]) >= 1

    # Check if openai has a multiplier > 1
    openai_mult = next(
        m for m in report["recommended_cost_multipliers"] if m["provider"] == "openai"
    )
    assert openai_mult["recommended_cost_multiplier"] > 1.0

    # Check if anthropic has a multiplier < 1
    anthropic_mult = next(
        m for m in report["recommended_cost_multipliers"] if m["provider"] == "anthropic"
    )
    assert anthropic_mult["recommended_cost_multiplier"] < 1.0


@pytest.mark.asyncio
async def test_calculate_estimation_error_with_outlier(session, monkeypatch):
    """
    Should not be heavily distorted by a single extreme outlier when trimmed mean is used.
    """
    monkeypatch.setenv("COMMERCIAL_CALIBRATION_USE_TRIMMED_MEAN", "true")
    monkeypatch.setenv("COMMERCIAL_CALIBRATION_OUTLIER_TRIM_PERCENT", "10")
    from app.core.config import get_settings

    get_settings.cache_clear()

    # Create 20 events with cost 1.0
    for _ in range(20):
        event = CommercialRoutingEvent(
            selected_provider="openai",
            selected_model="gpt-4",
            estimated_cost_brl=1.0,
            actual_cost_brl=1.0,
            created_at=datetime.now(UTC),
        )
        session.add(event)

    # Add 2 extreme outliers (top 10% of 22 is 2)
    for _ in range(2):
        event = CommercialRoutingEvent(
            selected_provider="openai",
            selected_model="gpt-4",
            estimated_cost_brl=1.0,
            actual_cost_brl=100.0,  # 100x cost!
            created_at=datetime.now(UTC),
        )
        session.add(event)

    await session.commit()

    result = await commercial_calibration.calculate_estimation_error(
        session, provider="openai", model="gpt-4", min_samples=20
    )

    # Without trimming, avg actual would be (20*1 + 2*100)/22 = 220/22 = 10.0 (900% error)
    # With trimming, the 2 outliers are removed.
    assert result["trimmed"] is True
    assert result["avg_actual_cost"] == 1.0  # Should be exactly 1.0 after trimming
    assert result["cost_error_percent"] == 0.0


@pytest.mark.asyncio
async def test_confidence_levels(session, monkeypatch):
    """
    Should return correct confidence levels based on sample count.
    """
    monkeypatch.setenv("COMMERCIAL_CALIBRATION_MIN_SAMPLES", "10")
    from app.core.config import get_settings

    get_settings.cache_clear()

    # Case 1: Low confidence (5 samples < 10)
    for _ in range(5):
        session.add(
            CommercialRoutingEvent(
                selected_provider="openai",
                selected_model="gpt-4",
                estimated_cost_brl=1.0,
                actual_cost_brl=1.0,
                created_at=datetime.now(UTC),
            )
        )
    await session.commit()
    result = await commercial_calibration.calculate_estimation_error(
        session, provider="openai", min_samples=10
    )
    assert result["confidence"] == "low"

    # Case 2: Medium confidence (15 samples >= 10 and < 50)
    for _ in range(10):
        session.add(
            CommercialRoutingEvent(
                selected_provider="openai",
                selected_model="gpt-4",
                estimated_cost_brl=1.0,
                actual_cost_brl=1.0,
                created_at=datetime.now(UTC),
            )
        )
    await session.commit()
    result = await commercial_calibration.calculate_estimation_error(
        session, provider="openai", min_samples=10
    )
    assert result["confidence"] == "medium"

    # Case 3: High confidence (55 samples >= 50)
    for _ in range(40):
        session.add(
            CommercialRoutingEvent(
                selected_provider="openai",
                selected_model="gpt-4",
                estimated_cost_brl=1.0,
                actual_cost_brl=1.0,
                created_at=datetime.now(UTC),
            )
        )
    await session.commit()
    result = await commercial_calibration.calculate_estimation_error(
        session, provider="openai", min_samples=10
    )
    assert result["confidence"] == "high"


def test_recommend_cost_multiplier_limits(monkeypatch):
    """
    Should respect the maximum recommended change per cycle.
    """
    monkeypatch.setenv("COMMERCIAL_CALIBRATION_MAX_RECOMMENDED_CHANGE_PERCENT", "25")
    from app.core.config import get_settings

    get_settings.cache_clear()

    # Case: Error is -50% (actual is 2x estimated).
    # multiplier = 1 / (1 - 0.5) = 2.0
    # But limit is 25%, so max multiplier is 1.25
    mult = commercial_calibration.recommend_cost_multiplier(-50.0, "high")
    assert mult == 1.25

    # Case: Error is 100% (estimated is 2x actual).
    # multiplier = 1 / (1 + 1.0) = 0.5
    # But limit is 25%, so min multiplier is 0.75
    mult = commercial_calibration.recommend_cost_multiplier(100.0, "high")
    assert mult == 0.75


@pytest.mark.asyncio
async def test_admin_endpoints_auth(admin_client, admin_token_headers):
    """
    Should require admin token for calibration endpoints.
    """
    # No token
    response = await admin_client.get("/admin/routing/calibration/report")
    assert response.status_code == 401  # Unauthorized

    # Valid token
    response = await admin_client.get(
        "/admin/routing/calibration/report", headers=admin_token_headers
    )
    assert response.status_code == 200
