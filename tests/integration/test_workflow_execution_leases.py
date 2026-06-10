from __future__ import annotations

import pytest
from app.core.time import utc_now
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.federated_execution import FederatedWorkflowExecutionService
from app.services.workflows.workflow_execution_leases import WorkflowExecutionLeaseService


@pytest.mark.asyncio
async def test_deterministic_lease_and_failover(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="lease-workflow",
        dag_or_steps=[{"stage_key": "stage-a", "config": {"model": "local"}}],
        client_id="tenant-a",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="lease-session",
        tenant_id="tenant-a",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="stage-a",
        input_data={"x": 1},
        output_data={"x": 1},
        state_snapshot={"step": 1},
    )
    fed = await FederatedWorkflowExecutionService().register_execution(
        session,
        execution_id=execution.id,
        region_id="sa-east-1",
        cluster_id="cluster-a",
        federation_mode="hybrid",
    )
    service = WorkflowExecutionLeaseService()
    candidates = ["node-c", "node-a", "node-b"]
    winner = service.deterministic_winner(workflow_id=fed.workflow_id, tenant_id=fed.tenant_id, candidates=candidates)
    lease = await service.acquire_lease(session, federated_execution_id=fed.id, candidates=candidates, ttl_seconds=10)
    lease.expires_at = utc_now()
    failover = await service.failover(session, federated_execution_id=fed.id, candidates=candidates, ttl_seconds=10)

    assert lease.lease_owner == winner
    assert failover.lease_owner in candidates
    assert failover.lease_owner != winner
    assert failover.lease_token > lease.lease_token


@pytest.mark.asyncio
async def test_lease_renew_requires_current_owner(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="lease-renew",
        dag_or_steps=[{"stage_key": "stage-a", "config": {"model": "local"}}],
        client_id="tenant-a",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="lease-renew-session",
        tenant_id="tenant-a",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="stage-a",
        input_data={"x": 1},
        output_data={"x": 1},
        state_snapshot={"step": 1},
    )
    fed = await FederatedWorkflowExecutionService().register_execution(
        session,
        execution_id=execution.id,
        region_id="sa-east-1",
        cluster_id="cluster-a",
        federation_mode="push",
    )
    service = WorkflowExecutionLeaseService()
    lease = await service.acquire_lease(
        session,
        federated_execution_id=fed.id,
        candidates=["node-a", "node-b"],
        ttl_seconds=10,
    )

    with pytest.raises(ValueError, match="lease_owner_mismatch"):
        await service.renew_lease(
            session,
            federated_execution_id=fed.id,
            lease_owner=f"{lease.lease_owner}-other",
            ttl_seconds=10,
        )
