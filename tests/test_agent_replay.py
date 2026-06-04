import pytest
from app.models.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentProfile,
    CommercialToolRegistry,
)
from app.services.agents.action_replay import verify_execution_replay
from app.services.agents.trusted_agent_runtime import trusted_agent_runtime
from sqlalchemy import select


@pytest.mark.asyncio
async def test_agent_replay_verifies_deterministic_execution(session):
    profile = CommercialAgentProfile(
        agent_name="Replay Worker",
        client_id="tenant-a",
        allowed_tools=["echo"],
        requires_approval_for_tools=False,
        confidential_runtime_required=False,
    )
    tool = CommercialToolRegistry(tool_name="echo", tenant_id="tenant-a", trust_status="trusted")
    session.add_all([profile, tool])
    await session.commit()
    await session.refresh(profile)

    execution = await trusted_agent_runtime.create_execution(
        session,
        agent_id=profile.id,
        tenant_id="tenant-a",
        session_id="replay-1",
        input_payload={"request": "run"},
        action_plan=[{"tool_name": "echo", "payload": {"value": "alpha"}}],
    )
    await session.commit()
    await trusted_agent_runtime.execute_plan(session, execution_id=execution.id)
    await session.commit()

    replay = await verify_execution_replay(session, execution_id=execution.id, verified_by="pytest")
    await session.commit()

    assert replay.verification_result == "verified"
    assert replay.mismatch_reason is None


@pytest.mark.asyncio
async def test_agent_replay_detects_receipt_tampering(session):
    profile = CommercialAgentProfile(
        agent_name="Replay Worker",
        client_id="tenant-a",
        allowed_tools=["echo"],
        requires_approval_for_tools=False,
        confidential_runtime_required=False,
    )
    tool = CommercialToolRegistry(tool_name="echo", tenant_id="tenant-a", trust_status="trusted")
    session.add_all([profile, tool])
    await session.commit()
    await session.refresh(profile)

    execution = await trusted_agent_runtime.create_execution(
        session,
        agent_id=profile.id,
        tenant_id="tenant-a",
        session_id="replay-2",
        input_payload={"request": "run"},
        action_plan=[{"tool_name": "echo", "payload": {"value": "beta"}}],
    )
    await session.commit()
    await trusted_agent_runtime.execute_plan(session, execution_id=execution.id)
    await session.commit()

    action = (
        await session.execute(
            select(CommercialAgentAction).where(CommercialAgentAction.execution_id == execution.id)
        )
    ).scalar_one()
    action.receipt_hash = "tampered"
    await session.commit()

    replay = await verify_execution_replay(session, execution_id=execution.id, verified_by="pytest")
    await session.commit()
    assert replay.verification_result == "invalid"
    assert replay.mismatch_reason == "receipt_invalid:0"
