from __future__ import annotations

import pytest
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator


async def _create_bundle(session, name: str) -> CommercialPolicyBundle:
    bundle = CommercialPolicyBundle(
        bundle_name=name,
        bundle_version="1",
        bundle_type="workflow",
        mode="enforce",
        status="active",
        rules_json={"allow": True},
        metadata_json={},
        immutable_hash=f"{name}-hash",
    )
    session.add(bundle)
    await session.flush()
    return bundle


@pytest.mark.asyncio
async def test_replay_session_deterministic_match(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    bundle = await _create_bundle(session, "replay-match")
    definition = await orchestrator.create_definition(
        session,
        name="replay-match-workflow",
        dag_or_steps=[
            {"stage_key": "stage-a", "policy": {"bundle_ref": str(bundle.id)}, "config": {"x": 1}}
        ],
    )
    original = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="orig", tenant_id="tenant-a"
    )
    replay = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="replay", tenant_id="tenant-a"
    )
    await orchestrator.complete_stage(
        session,
        execution_id=original.id,
        stage_key="stage-a",
        input_data={"x": 1},
        output_data={"ok": True},
    )
    await orchestrator.complete_stage(
        session,
        execution_id=replay.id,
        stage_key="stage-a",
        input_data={"x": 1},
        output_data={"ok": True},
    )

    replay_session = await orchestrator.create_replay_session(
        session,
        original_execution_id=original.id,
        replay_execution_id=replay.id,
        requested_by="auditor",
        tenant_id="tenant-a",
    )
    replay_session = await orchestrator.finalize_replay_session(session, replay_session.id)

    assert replay_session.session_status == "completed"
    assert replay_session.policy_mismatch_detected is False
    assert replay_session.mismatch_detected is False


@pytest.mark.asyncio
async def test_replay_session_detects_mismatch(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    bundle = await _create_bundle(session, "replay-drift")
    definition = await orchestrator.create_definition(
        session,
        name="replay-drift-workflow",
        dag_or_steps=[
            {"stage_key": "stage-a", "policy": {"bundle_ref": str(bundle.id)}, "config": {"x": 1}}
        ],
    )
    original = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="orig-2", tenant_id="tenant-a"
    )
    replay = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="replay-2", tenant_id="tenant-a"
    )
    await orchestrator.complete_stage(
        session,
        execution_id=original.id,
        stage_key="stage-a",
        input_data={"x": 1},
        output_data={"ok": True},
    )
    await orchestrator.complete_stage(
        session,
        execution_id=replay.id,
        stage_key="stage-a",
        input_data={"x": 1},
        output_data={"ok": False},
    )

    replay_session = await orchestrator.create_replay_session(
        session,
        original_execution_id=original.id,
        replay_execution_id=replay.id,
        requested_by="auditor",
        tenant_id="tenant-a",
    )
    replay_session = await orchestrator.finalize_replay_session(session, replay_session.id)

    assert replay_session.session_status == "drift_detected"
    assert replay_session.mismatch_detected is True
