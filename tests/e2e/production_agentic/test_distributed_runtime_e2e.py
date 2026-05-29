from pathlib import Path

import pytest

from app.services.distributed_runtime.cluster_registry import ClusterRegistry
from app.services.distributed_runtime.job_placement import JobPlacementService
from app.services.runtime.distributed_runtime import DistributedRuntimeService
from app.models.runtime.distributed_runtime import DistributedAgentJob


@pytest.mark.asyncio
async def test_distributed_runtime_registration_and_placement(session):
    runtime = DistributedRuntimeService(session)
    cluster_registry = ClusterRegistry(session)

    cluster = await cluster_registry.register_cluster("e2e-cluster", "sa-east-1", is_managed=True)
    local_node = await runtime.register_node(
        {
            "name": "e2e-local-node",
            "base_url": "http://localhost:18081",
            "node_type": "local",
            "cpu_count": 4,
        }
    )
    await runtime.record_heartbeat(local_node.id, {"cpu_usage_percent": 12.5, "active_requests": 1})

    job = DistributedAgentJob(job_type="AgentRun", tenant_id="tenant-e2e")
    session.add(job)
    await session.commit()

    placed = await JobPlacementService(session).place_job(job)

    assert cluster.is_managed is True
    assert placed is not None
    assert placed.name == "e2e-local-node"

    artifact = Path("artifacts/e2e/production-agentic/distributed-runtime.md")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "## Distributed Runtime E2E\n- Cluster registry: Real DB-backed\n- Node registration and heartbeat: Real\n- Placement policy: Real local-first resolution\n",
        encoding="utf-8",
    )
