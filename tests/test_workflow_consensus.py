from __future__ import annotations

import pytest

from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.federated_consensus import FederatedWorkflowConsensusService
from app.services.workflows.federated_execution import FederatedWorkflowExecutionService


@pytest.mark.asyncio
async def test_consensus_mismatch_and_reconciliation(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="consensus-workflow",
        dag_or_steps=[{"stage_key": "stage-a", "config": {"model": "local"}}],
        client_id="tenant-a",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="consensus-session",
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
    fed_service = FederatedWorkflowExecutionService()
    fed = await fed_service.register_execution(
        session,
        execution_id=execution.id,
        region_id="sa-east-1",
        cluster_id="cluster-a",
        federation_mode="hybrid",
    )
    peer_ok = await fed_service.register_peer(
        session,
        federated_execution_id=fed.id,
        peer_cluster_id="cluster-b",
        peer_region_id="us-east-1",
    )
    peer_bad = await fed_service.register_peer(
        session,
        federated_execution_id=fed.id,
        peer_cluster_id="cluster-c",
        peer_region_id="eu-west-1",
    )
    peer_ok.execution_hash = fed.execution_hash
    peer_bad.execution_hash = "0" * 64
    consensus = FederatedWorkflowConsensusService()

    result = await consensus.validate_consensus(session, federated_execution_id=fed.id)
    reconciled = await consensus.reconcile_execution(session, federated_execution_id=fed.id)

    assert result["consensus_status"] in {"mismatch_detected", "quorum_failed"}
    assert reconciled["consensus_status"] == "reconciled"


@pytest.mark.asyncio
async def test_consensus_quorum_validation(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="consensus-quorum",
        dag_or_steps=[{"stage_key": "stage-a", "config": {"model": "local"}}],
        client_id="tenant-a",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="consensus-quorum",
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
    fed_service = FederatedWorkflowExecutionService()
    fed = await fed_service.register_execution(
        session,
        execution_id=execution.id,
        region_id="sa-east-1",
        cluster_id="cluster-a",
        federation_mode="push",
    )
    peer = await fed_service.register_peer(
        session,
        federated_execution_id=fed.id,
        peer_cluster_id="cluster-b",
        peer_region_id="us-east-1",
    )
    peer.execution_hash = fed.execution_hash

    result = await FederatedWorkflowConsensusService().validate_consensus(session, federated_execution_id=fed.id)

    assert result["consensus_status"] == "verified"
    assert result["canonical_hash"] == fed.execution_hash
