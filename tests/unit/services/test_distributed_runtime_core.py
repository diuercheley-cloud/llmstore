from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.distributed_runtime.cluster_heartbeat import ClusterHeartbeatService
from app.services.distributed_runtime.node_registry import NodeRegistry


@pytest.mark.asyncio
async def test_node_registry_returns_all_nodes():
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["node-a", "node-b"]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    assert await NodeRegistry(db).list_nodes() == ["node-a", "node-b"]


def test_cluster_heartbeat_health_score_fails_closed_for_offline_nodes():
    assert ClusterHeartbeatService._compute_health_score(10, 10, 10, "offline") == 0
    assert ClusterHeartbeatService._compute_health_score(10, 20, 30, "active") == pytest.approx(82)
