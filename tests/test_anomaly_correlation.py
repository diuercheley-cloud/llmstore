import uuid
from datetime import datetime

import pytest
from app.models.commercial_runtime_fabric import CommercialRuntimeFabricEvent
from app.services.runtime.anomaly_correlation import AnomalyCorrelator
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_anomaly_correlation_drift(session: AsyncSession):
    event = CommercialRuntimeFabricEvent(
        id=str(uuid.uuid4()),
        event_type="drift_detected",
        severity="warning",
        source_node_id="node-1",
        component="workflow",
        details={"drift_id": "drift-123"},
        created_at=datetime.utcnow()
    )
    session.add(event)
    await session.commit()

    correlator = AnomalyCorrelator(session)
    anomalies = await correlator.process_latest_metrics(client_id="test-client")

    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == "drift"
    assert anomalies[0].source_id == "node-1"
