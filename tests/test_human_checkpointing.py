import pytest

from app.models.commercial_autonomous_guardrails import CommercialAutonomousExecutionPolicy
from app.services.governance.human_checkpointing import HumanCheckpointingService


@pytest.mark.asyncio
async def test_human_checkpointing_multi_stage_approval(session):
    service = HumanCheckpointingService()
    policy = CommercialAutonomousExecutionPolicy(
        policy_name="workflow-approval",
        action_type="safe_throttle",
        tenant_id="tenant-a",
        approval_stages_json=[
            {"stage": 1, "required_approvals": 1},
            {"stage": 2, "required_approvals": 2},
        ],
        require_human_approval=True,
        max_blast_radius_score=0.8,
        mode="guarded_enforce",
        is_active=True,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)

    checkpoints = await service.create_checkpoints(
        session,
        policy=policy,
        request={
            "action_type": "safe_throttle",
            "target_type": "runtime_node",
            "target_id": "node-1",
            "tenant_id": "tenant-a",
        },
    )

    assert len(checkpoints) == 2
    assert checkpoints[1].required_approvals == 2

    await service.approve_checkpoint(session, checkpoint_id=checkpoints[0].id, approver="alice")
    await service.approve_checkpoint(session, checkpoint_id=checkpoints[1].id, approver="bob")
    await service.approve_checkpoint(session, checkpoint_id=checkpoints[1].id, approver="carol")

    result = await service.validate_chain(
        session,
        policy_id=policy.id,
        target_type="runtime_node",
        target_id="node-1",
        tenant_id="tenant-a",
    )
    assert result["approved"] is True
    assert result["approval_hash"]


@pytest.mark.asyncio
async def test_human_checkpoint_rejection_blocks_chain(session):
    service = HumanCheckpointingService()
    checkpoints = await service.create_checkpoints(
        session,
        policy=None,
        request={
            "action_type": "safe_throttle",
            "target_type": "runtime_node",
            "target_id": "node-2",
            "tenant_id": "tenant-a",
        },
    )

    rejected = await service.reject_checkpoint(
        session,
        checkpoint_id=checkpoints[0].id,
        approver="dave",
        reason="out_of_window",
    )
    result = await service.validate_chain(
        session,
        target_type="runtime_node",
        target_id="node-2",
        tenant_id="tenant-a",
    )

    assert rejected.status == "rejected"
    assert result["approved"] is False
    assert result["reason"] == "checkpoint_pending"
