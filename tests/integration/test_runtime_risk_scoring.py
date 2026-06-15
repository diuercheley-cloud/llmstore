import pytest
from app.models.commercial.commercial_predictive_aiops import (
    CommercialAnomalySignal,
    CommercialFailurePrediction,
)
from app.services.runtime.runtime_risk_scoring import RuntimeRiskScorer
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_runtime_risk_scoring(session: AsyncSession):
    anomalies = [CommercialAnomalySignal(anomaly_type="drift")]
    forecasts = [CommercialFailurePrediction(prediction_type="node_failure")]

    scorer = RuntimeRiskScorer(session)
    trends = await scorer.update_risk_trends(
        client_id="test-client", anomalies=anomalies, forecasts=forecasts
    )

    assert len(trends) == 1
    assert trends[0].risk_type == "operational"
    # 0.1 (anomaly) + 0.2 (forecast) = 0.3
    assert trends[0].risk_score == pytest.approx(0.3)
    assert trends[0].trend_direction == "stable"  # < 0.5
