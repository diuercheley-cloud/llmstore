import pytest
from app.models.commercial.commercial_agents import (
    CommercialAgentAction,
    CommercialAgentProfile,
    CommercialToolRegistry,
)
from app.services.agents.trusted_agent_runtime import trusted_agent_runtime
from sqlalchemy import select


@pytest.mark.asyncio
async def test_trusted_runtime_executes_registered_tool(session):
    profile = CommercialAgentProfile(
        agent_name="Trusted Worker",
        client_id="tenant-a",
        allowed_tools=["echo"],
        requires_approval_for_tools=False,
        confidential_runtime_required=False,
    )
    tool = CommercialToolRegistry(
        tool_name="echo",
        tenant_id="tenant-a",
        trust_status="trusted",
        requires_approval=False,
        confidential_payload_mode="redacted",
    )
    session.add_all([profile, tool])
    await session.commit()
    await session.refresh(profile)

    execution = await trusted_agent_runtime.create_execution(
        session,
        agent_id=profile.id,
        tenant_id="tenant-a",
        session_id="sess-1",
        input_payload={"request": "run"},
        action_plan=[{"tool_name": "echo", "payload": {"value": "secret-value"}}],
        dry_run=False,
    )
    await session.commit()

    await trusted_agent_runtime.execute_plan(session, execution_id=execution.id)
    await session.commit()
    await session.refresh(execution)

    action = (
        await session.execute(
            select(CommercialAgentAction).where(CommercialAgentAction.execution_id == execution.id)
        )
    ).scalar_one()
    assert execution.status == "completed"
    assert execution.audit_chain_hash is not None
    assert action.receipt_hash is not None
    assert action.result_hash is not None
    assert "secret-value" not in str(action.metadata_json)


@pytest.mark.asyncio
async def test_trusted_runtime_blocks_tenant_scope_violation(session):
    profile = CommercialAgentProfile(
        agent_name="Scoped Worker",
        client_id="tenant-a",
        allowed_tools=["echo"],
        requires_approval_for_tools=False,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    with pytest.raises(ValueError, match="tenant_scope_violation"):
        await trusted_agent_runtime.create_execution(
            session,
            agent_id=profile.id,
            tenant_id="tenant-b",
            session_id="sess-2",
            input_payload={},
            action_plan=[{"tool_name": "echo", "payload": {}}],
        )
