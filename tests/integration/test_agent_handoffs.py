import uuid

import pytest
from app.core.config import get_settings
from app.services.agents import agent_state
from app.services.agents.agent_handoffs import AgentHandoffService, HandoffDeniedError


@pytest.mark.asyncio
async def test_handoff_disabled_blocks(session):
    settings = get_settings()
    settings.agent_handoffs_enabled = False

    service = AgentHandoffService(session)
    with pytest.raises(HandoffDeniedError, match="disabled"):
        await service.initiate_handoff(uuid.uuid4(), uuid.uuid4(), "test", {})


@pytest.mark.asyncio
async def test_handoff_policy_required(session):
    settings = get_settings()
    settings.agent_handoffs_enabled = True

    # Create agents first so policy engine can find them
    agent_a = uuid.uuid4()
    agent_b = uuid.uuid4()
    await agent_state.create_agent_definition(
        session,
        {
            "id": agent_a,
            "name": "A",
            "version": "1",
            "instructions": "i",
            "model_id": "m",
            "owner": "o",
        },
    )
    await agent_state.create_agent_definition(
        session,
        {
            "id": agent_b,
            "name": "B",
            "version": "1",
            "instructions": "i",
            "model_id": "m",
            "owner": "o",
        },
    )

    run_a = await agent_state.create_agent_run(session, agent_a, "t1", "input")

    service = AgentHandoffService(session)

    # Try handoff without policy
    with pytest.raises(HandoffDeniedError, match="No handoff policy found"):
        await service.initiate_handoff(run_a.id, agent_b, "need help", {})

    # Create policy
    await service.create_handoff_policy(
        {
            "tenant_id": "t1",
            "source_agent_id": agent_a,
            "target_agent_id": agent_b,
            "max_handoffs_per_run": 2,
        }
    )

    target_run_id = await service.initiate_handoff(run_a.id, agent_b, "need help", {})
    assert target_run_id is not None


@pytest.mark.asyncio
async def test_max_handoff_loop_prevention(session):
    settings = get_settings()
    settings.agent_handoffs_enabled = True

    agent_a = uuid.uuid4()
    agent_b = uuid.uuid4()
    await agent_state.create_agent_definition(
        session,
        {
            "id": agent_a,
            "name": "A",
            "version": "1",
            "instructions": "i",
            "model_id": "m",
            "owner": "o",
        },
    )
    await agent_state.create_agent_definition(
        session,
        {
            "id": agent_b,
            "name": "B",
            "version": "1",
            "instructions": "i",
            "model_id": "m",
            "owner": "o",
        },
    )

    run_a = await agent_state.create_agent_run(session, agent_a, "t1", "input")

    service = AgentHandoffService(session)
    await service.create_handoff_policy(
        {
            "tenant_id": "t1",
            "source_agent_id": agent_a,
            "target_agent_id": agent_b,
            "max_handoffs_per_run": 1,
        }
    )

    # First handoff OK
    await service.initiate_handoff(run_a.id, agent_b, "help 1", {})

    # Second handoff should fail (max reached)
    # We use the same root_run_id to simulate the session
    with pytest.raises(HandoffDeniedError, match="Maximum handoffs reached"):
        await service.initiate_handoff(run_a.id, agent_b, "help 2", {})
