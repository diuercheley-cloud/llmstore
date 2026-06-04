import uuid

import pytest
from app.models.commercial_runtime_fabric import CommercialRuntimeFabricHealth
from app.services.runtime.failure_forecasting import FailureForecaster
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_failure_forecasting_node_exhaustion(session: AsyncSession):
    node_id = str(uuid.uuid4())
    health = CommercialRuntimeFabricHealth(
        id=str(uuid.uuid4()),
        node_id=node_id,
        status="healthy",
        metrics={"cpu": 98, "mem": 40}
    )
    session.add(health)
    await session.commit()

    forecaster = FailureForecaster(session)
    forecasts = await forecaster.generate_forecasts(client_id="test-client", anomalies=[])

    assert len(forecasts) == 1
    assert forecasts[0].prediction_type == "node_failure"
    assert forecasts[0].confidence_score == 0.85
    assert forecasts[0].target_id == node_id
