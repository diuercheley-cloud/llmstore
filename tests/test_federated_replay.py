from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.commercial_workflows import CommercialWorkflowStage
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.federated_execution import FederatedWorkflowExecutionService
from app.services.workflows.federated_replay import FederatedWorkflowReplayService


async def _build_execution(session, *, session_id: str, summary: str):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name=f"replay-{session_id}",
        dag_or_steps=[
            {"stage_key": "summarize", "config": {"model": "local"}},
            {"stage_key": "classify", "dependencies": ["summarize"], "config": {"model": "local"}},
        ],
        client_id="tenant-a",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id=session_id,
        tenant_id="tenant-a",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="summarize",
        input_data={"text": "hello"},
        output_data={"summary": summary},
        state_snapshot={"step": 1},
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="classify",
        input_data={"summary": summary},
        output_data={"label": "ok"},
        state_snapshot={"step": 2},
    )
    await session.flush()
    return execution


@pytest.mark.asyncio
async def test_federated_replay_verifies_and_exports_offline_bundle(session):
    source = await _build_execution(session, session_id="src", summary="hello")
    fed = await FederatedWorkflowExecutionService().register_execution(
        session,
        execution_id=source.id,
        region_id="sa-east-1",
        cluster_id="cluster-a",
        federation_mode="sovereign_airgap",
        sovereign_mode="sovereign_airgap",
    )
    replay_service = FederatedWorkflowReplayService()
    report = await replay_service.validate_replay(session, federated_execution_id=fed.id)
    bundle = await replay_service.export_signed_bundle(session, report_id=report.id)
    verification = await replay_service.verify_offline_bundle(session, bundle=bundle)

    assert report.replay_status == "verified"
    assert report.drift_score == 0.0
    assert verification["valid"] is True


@pytest.mark.asyncio
async def test_federated_replay_detects_drift(session):
    source = await _build_execution(session, session_id="src-drift", summary="hello")
    replay = await _build_execution(session, session_id="replay-drift", summary="different")
    replay_stage = (
        await session.execute(
            select(CommercialWorkflowStage)
            .where(CommercialWorkflowStage.execution_id == replay.id, CommercialWorkflowStage.stage_key == "classify")
        )
    ).scalar_one()
    replay_stage.stage_hash = "f" * 64
    fed = await FederatedWorkflowExecutionService().register_execution(
        session,
        execution_id=source.id,
        region_id="sa-east-1",
        cluster_id="cluster-a",
        federation_mode="hybrid",
    )
    report = await FederatedWorkflowReplayService().validate_replay(
        session,
        federated_execution_id=fed.id,
        replay_execution_id=replay.id,
    )

    assert report.mismatch_detected is True
    assert report.replay_status == "mismatch_detected"
    assert report.drift_score > 0.0
