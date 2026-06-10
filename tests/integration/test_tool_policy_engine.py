import pytest
from app.models.commercial.commercial_agents import (
    CommercialAgentExecution,
    CommercialAgentProfile,
    CommercialToolRegistry,
)
from app.services.agents.tool_policy_engine import ToolPolicyEngine


@pytest.mark.asyncio
async def test_policy_engine_denies_unregistered_tool(session):
    profile = CommercialAgentProfile(
        agent_name="Policy Worker",
        client_id="tenant-a",
        allowed_tools=["echo"],
        requires_approval_for_tools=False,
    )
    execution = CommercialAgentExecution(agent_id=profile.id, tenant_id="tenant-a", status="running")
    session.add(profile)
    await session.flush()
    execution.agent_id = profile.id
    session.add(execution)
    await session.commit()

    engine = ToolPolicyEngine()
    decision = await engine.evaluate_action(
        session,
        profile=profile,
        execution=execution,
        tool_name="echo",
        payload={"value": "x"},
    )
    assert decision.allowed is False
    assert decision.reason == "tool_not_registered"


@pytest.mark.asyncio
async def test_policy_engine_requires_approval_and_enforces_tenant(session):
    profile = CommercialAgentProfile(
        agent_name="Policy Worker",
        client_id="tenant-a",
        allowed_tools=["echo"],
        requires_approval_for_tools=False,
    )
    tool = CommercialToolRegistry(
        tool_name="echo",
        tenant_id="tenant-a",
        trust_status="trusted",
        requires_approval=True,
    )
    session.add_all([profile, tool])
    await session.flush()
    execution = CommercialAgentExecution(agent_id=profile.id, tenant_id="tenant-a", status="running")
    session.add(execution)
    await session.commit()

    engine = ToolPolicyEngine()
    decision = await engine.evaluate_action(
        session,
        profile=profile,
        execution=execution,
        tool_name="echo",
        payload={"value": "x"},
    )
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.decision == "pending_approval"

    execution.tenant_id = "tenant-b"
    tenant_mismatch = await engine.evaluate_action(
        session,
        profile=profile,
        execution=execution,
        tool_name="echo",
        payload={"value": "x"},
    )
    assert tenant_mismatch.allowed is False
    assert tenant_mismatch.reason in {"tenant_scope_mismatch", "agent_profile_tenant_mismatch", "tool_not_registered"}
