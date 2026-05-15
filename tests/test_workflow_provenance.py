import pytest

from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.workflow_provenance import WorkflowProvenanceService


@pytest.mark.asyncio
async def test_workflow_provenance_and_drift_detection(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    provenance = WorkflowProvenanceService()
    definition = await orchestrator.create_definition(
        session,
        name="provenance-flow",
        dag_or_steps=[{"stage_key": "stage-1", "config": {"seed": 1}}],
        client_id="tenant-p",
    )

    original = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="orig",
        tenant_id="tenant-p",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=original.id,
        stage_key="stage-1",
        input_data={"x": 1},
        output_data={"result": "A"},
    )

    replay_exec = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="replay",
        tenant_id="tenant-p",
        replay_of_execution_id=original.id,
    )
    await orchestrator.complete_stage(
        session,
        execution_id=replay_exec.id,
        stage_key="stage-1",
        input_data={"x": 1},
        output_data={"result": "B"},
    )
    await session.commit()

    prov = await provenance.build_execution_provenance(session, original)
    drift = await provenance.detect_pipeline_drift(session, original.id, replay_exec.id)

    assert prov["provenance_hash"] is not None
    assert prov["stages"][0]["stage_key"] == "stage-1"
    assert drift["drift_detected"] is True
    assert drift["mismatches"][0]["stage_key"] == "stage-1"
