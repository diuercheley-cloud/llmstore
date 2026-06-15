from __future__ import annotations

import pytest
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.models.commercial.commercial_workflows import CommercialWorkflowStage
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.workflow_policy_enforcement import WorkflowPolicyEnforcementService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_bundle(
    session: AsyncSession, *, name: str = "wf-policy"
) -> CommercialPolicyBundle:
    bundle = CommercialPolicyBundle(
        bundle_name=name,
        bundle_version="1.0.0",
        bundle_type="workflow",
        mode="enforce",
        status="active",
        rules_json={"approval_required": False, "allow": True},
        metadata_json={"scope": "workflow"},
        immutable_hash=f"hash-{name}",
    )
    session.add(bundle)
    await session.flush()
    return bundle


@pytest.mark.asyncio
async def test_enforcement_deny_by_default(session: AsyncSession):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="deny-by-default",
        dag_or_steps=[{"stage_key": "stage-a", "policy": {}, "config": {"x": 1}}],
    )
    execution = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="s-1", tenant_id="tenant-a"
    )
    stage = (
        await session.execute(
            select(CommercialWorkflowStage).where(
                CommercialWorkflowStage.execution_id == execution.id
            )
        )
    ).scalar_one()

    decision = await WorkflowPolicyEnforcementService().evaluate_stage(
        session, execution=execution, stage=stage
    )

    assert decision["decision"] == "deny"
    assert decision["reason"] == "missing_valid_policy"
    assert stage.policy_gate_status == "denied"


@pytest.mark.asyncio
async def test_policy_snapshot_drift_and_rollback(session: AsyncSession):
    orchestrator = DeterministicWorkflowOrchestrator()
    bundle = await _create_bundle(session)
    definition = await orchestrator.create_definition(
        session,
        name="policy-drift",
        dag_or_steps=[
            {
                "stage_key": "stage-a",
                "policy": {"bundle_ref": str(bundle.id), "enforcement_mode": "enforce"},
                "runtime": {"cpu": "small"},
                "config": {"x": 1},
            }
        ],
    )
    execution = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="s-2", tenant_id="tenant-a"
    )
    stage = (
        await session.execute(
            select(CommercialWorkflowStage).where(
                CommercialWorkflowStage.execution_id == execution.id
            )
        )
    ).scalar_one()

    stage.metadata_json["runtime"] = {"cpu": "large"}
    decision = await WorkflowPolicyEnforcementService().evaluate_stage(
        session, execution=execution, stage=stage
    )
    rollback = await WorkflowPolicyEnforcementService().rollback_stage_policy(
        session,
        execution=execution,
        stage=stage,
        actor_id="admin",
    )

    assert decision["drift_detected"] is True
    assert stage.drift_status == "drift_detected"
    assert rollback.binding_status == "rolled_back"
    assert rollback.rollback_from_binding_id is not None
