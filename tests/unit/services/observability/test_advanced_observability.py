# Owner: agent-platform
import logging
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.observability.anomaly_detection import AnomalyDetectionService
from app.services.observability.log_correlation import LogCorrelationService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)


def test_log_correlation_context():
    run_id = uuid.uuid4()
    trace_id = "trace-123"

    # We use a standard logger to test the adapter
    base_logger = logging.getLogger("test_correlate")
    adapter = LogCorrelationService.get_logger("test_correlate", run_id=run_id, trace_id=trace_id)

    # We can't easily assert the internal dictionary of LoggerAdapter in all Python versions,
    # but we can verify it doesn't crash and provides the interface.
    assert adapter.extra["run_id"] == str(run_id)
    assert adapter.extra["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_anomaly_detection_cost_spike(mock_db):
    service = AnomalyDetectionService(mock_db)
    agent_id = uuid.uuid4()

    # Mocking historical average (low) and current cost (high)
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=lambda: 1.0),  # avg 24h: 1.0
            MagicMock(scalar_one_or_none=lambda: 10.0),  # last hour: 10.0
        ]
    )

    # Threshold 2.0x, current 10x
    is_anomaly = await service.detect_cost_spike(agent_id, threshold_multiplier=2.0)
    assert is_anomaly is True


@pytest.mark.asyncio
async def test_anomaly_detection_no_spike(mock_db):
    service = AnomalyDetectionService(mock_db)
    agent_id = uuid.uuid4()

    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=lambda: 1.0),
            MagicMock(scalar_one_or_none=lambda: 1.1),
        ]
    )

    is_anomaly = await service.detect_cost_spike(agent_id)
    assert is_anomaly is False
