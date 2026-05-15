import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.runtime.predictive_aiops import PredictiveAIOpsService
from app.models.commercial_predictive_aiops import (
    CommercialFailurePrediction,
    CommercialAnomalySignal,
    CommercialRuntimeRiskTrend,
    CommercialAIOpsRecommendation
)
from app.models.commercial_runtime_fabric import CommercialRuntimeFabricHealth, CommercialRuntimeFabricEvent
import uuid

@pytest.mark.asyncio
async def test_predictive_aiops_cycle(session: AsyncSession):
    # Setup: Create some data to trigger AIOps
    node_id = str(uuid.uuid4())
    health = CommercialRuntimeFabricHealth(
        id=str(uuid.uuid4()),
        node_id=node_id,
        status="degraded",
        metrics={"cpu": 95, "mem": 80}
    )
    session.add(health)
    
    drift_event = CommercialRuntimeFabricEvent(
        id=str(uuid.uuid4()),
        event_type="drift_detected",
        severity="warning",
        source_node_id=node_id,
        component="workflow",
        details={"workflow_id": "test-wf"}
    )
    session.add(drift_event)
    await session.commit()

    service = PredictiveAIOpsService(session)
    result = await service.run_cycle(client_id="test-client")

    assert result["anomalies_detected"] > 0
    assert result["forecasts_generated"] > 0
    assert result["risk_trends_updated"] > 0
    assert result["recommendations_generated"] > 0

    # Verify recommendations
    from sqlalchemy import select
    stmt = select(CommercialAIOpsRecommendation).filter(CommercialAIOpsRecommendation.client_id == "test-client")
    res = await session.execute(stmt)
    recs = res.scalars().all()
    assert len(recs) > 0
    assert recs[0].action_type in ["isolate_node", "throttle_tenant", "replay_workflow"]
