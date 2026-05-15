from __future__ import annotations

import pytest

from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.federated_execution import FederatedWorkflowExecutionService


async def _completed_execution(session, *, tenant_id: str = "tenant-a"):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="fed-workflow",
        dag_or_steps={
            "stages": [
                {"stage_key": "ingest", "dependencies": [], "config": {"model": "local"}},
                {"stage_key": "score", "dependencies": ["ingest"], "config": {"model": "local"}},
            ]
        },
        client_id=tenant_id,
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id=f"{tenant_id}-session",
        tenant_id=tenant_id,
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="ingest",
        input_data={"payload": "alpha"},
        output_data={"result": "alpha"},
        state_snapshot={"step": 1},
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="score",
        input_data={"payload": "alpha"},
        output_data={"score": 1},
        state_snapshot={"step": 2},
    )
    await session.flush()
    return execution


@pytest.mark.asyncio
async def test_federated_execution_registers_partition_and_forwarding(session):
    execution = await _completed_execution(session)
    service = FederatedWorkflowExecutionService()
    row = await service.register_execution(
        session,
        execution_id=execution.id,
        region_id="sa-east-1",
        cluster_id="cluster-local",
        federation_mode="hybrid",
        peer_clusters=[
            {"cluster_id": "cluster-1", "region_id": "us-east-1"},
            {"cluster_id": "cluster-2", "region_id": "eu-west-1"},
        ],
    )
    forwarded = await service.forward_execution(
        session,
        federated_execution_id=row.id,
        target_cluster_id="cluster-1",
    )

    assert row.execution_hash
    assert row.stage_ownership_json
    assert set(row.stage_ownership_json) == {"ingest", "score"}
    assert forwarded["target_cluster_id"] == "cluster-1"
    assert forwarded["bundle_signature"].startswith("ed25519_placeholder:")


@pytest.mark.asyncio
async def test_federated_execution_enforces_tenant_isolation(session):
    execution = await _completed_execution(session, tenant_id="tenant-iso")
    service = FederatedWorkflowExecutionService()

    with pytest.raises(ValueError, match="tenant_scope_violation"):
        await service.register_execution(
            session,
            execution_id=execution.id,
            region_id="sa-east-1",
            cluster_id="cluster-local",
            federation_mode="push",
            client_id="another-tenant",
        )
