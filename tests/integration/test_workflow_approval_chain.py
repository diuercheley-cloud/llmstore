from __future__ import annotations

from datetime import timedelta

import pytest
from app.core.time import utc_now
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.models.commercial.commercial_workflows import (
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowStage,
)
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.workflow_approval_chain import WorkflowApprovalChainService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _setup_execution(session: AsyncSession):
    bundle = CommercialPolicyBundle(
        bundle_name="wf-approval",
        bundle_version="1.0.0",
        bundle_type="workflow",
        mode="enforce",
        status="active",
        rules_json={"approval_required": True},
        metadata_json={},
        immutable_hash="wf-approval-hash",
    )
    session.add(bundle)
    await session.flush()
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="approval-flow",
        dag_or_steps=[
            {
                "stage_key": "stage-a",
                "policy": {
                    "bundle_ref": str(bundle.id),
                    "approval_required": True,
                    "approvers": ["approver-1", "approver-2"],
                },
                "config": {"x": 1},
            }
        ],
    )
    execution = await orchestrator.start_execution(
        session, definition_id=definition.id, session_id="approval-session", tenant_id="tenant-a"
    )
    stage = (
        await session.execute(
            select(CommercialWorkflowStage).where(
                CommercialWorkflowStage.execution_id == execution.id
            )
        )
    ).scalar_one()
    snapshot = await session.get(CommercialWorkflowPolicySnapshot, stage.active_policy_snapshot_id)
    return execution, stage, snapshot


@pytest.mark.asyncio
async def test_multi_step_approval_and_delegation(session: AsyncSession):
    execution, stage, snapshot = await _setup_execution(session)
    service = WorkflowApprovalChainService()

    rows = await service.request_approval(
        session,
        execution=execution,
        stage=stage,
        snapshot=snapshot,
        requested_by="requester",
        approvers=["approver-1", "approver-2"],
        delegated_approvers=["approver-2"],
    )
    await service.record_decision(
        session,
        execution=execution,
        stage=stage,
        chain_id=rows[0].chain_id,
        approver="approver-1",
        status="approved",
    )
    await service.record_decision(
        session,
        execution=execution,
        stage=stage,
        chain_id=rows[0].chain_id,
        approver="approver-2",
        status="approved",
        actor_metadata={"delegated": True},
    )

    assert stage.approval_status == "approved"
    assert rows[1].delegated_by == "requester"


@pytest.mark.asyncio
async def test_approval_expiration(session: AsyncSession):
    execution, stage, snapshot = await _setup_execution(session)
    service = WorkflowApprovalChainService()

    rows = await service.request_approval(
        session,
        execution=execution,
        stage=stage,
        snapshot=snapshot,
        requested_by="requester",
        approvers=["approver-1"],
        ttl_seconds=1,
    )
    rows[0].expires_at = utc_now() - timedelta(seconds=1)

    try:
        await service.record_decision(
            session,
            execution=execution,
            stage=stage,
            chain_id=rows[0].chain_id,
            approver="approver-1",
            status="approved",
        )
        assert False, "expected approval_expired"
    except ValueError as exc:
        assert str(exc) == "approval_expired"
