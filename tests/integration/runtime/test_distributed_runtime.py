import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.runtime.distributed_runtime import DistributedRuntimeService


@pytest.mark.asyncio
async def test_register_node_mock():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    # Mocking that no node exists yet
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    service = DistributedRuntimeService(mock_db)
    node_data = {
        "name": "test-node",
        "base_url": "http://test-node:8081",
        "node_type": "remote",
        "gpu_count": 1,
        "memory_total_mb": 16384,
    }

    node = await service.register_node(node_data)
    assert node.name == "test-node"
    assert node.status == "ready"
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_record_heartbeat_mock():
    mock_db = AsyncMock()
    service = DistributedRuntimeService(mock_db)
    node_id = uuid.uuid4()

    heartbeat_data = {"cpu_usage_percent": 50.0, "active_requests": 5}
    await service.record_heartbeat(node_id, heartbeat_data)

    assert mock_db.execute.called
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_drain_node_mock():
    mock_db = AsyncMock()
    service = DistributedRuntimeService(mock_db)
    node_id = uuid.uuid4()

    await service.drain_node(node_id)
    assert mock_db.execute.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_update_node_statuses_mock():
    mock_db = AsyncMock()
    service = DistributedRuntimeService(mock_db)

    await service.update_node_statuses()
    assert mock_db.execute.called
    assert mock_db.commit.called
