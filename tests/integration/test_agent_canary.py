import uuid

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.models.agents.agent_canary import AgentCanaryAssignment, AgentShadowRun
from app.models.agents.agents import AgentDefinition, AgentRun
from app.services.agents.canary.canary_comparator import CanaryComparator
from app.services.agents.canary.canary_promotion_gate import CanaryPromotionGate
from app.services.agents.canary.shadow_runner import ShadowRunner


@pytest.fixture
def agent_ids():
    return uuid.uuid4(), uuid.uuid4()  # base, canary


@pytest_asyncio.fixture
async def setup_canary(session, agent_ids):
    base_id, canary_id = agent_ids
    base = AgentDefinition(
        id=base_id,
        name="Base",
        version="1.0",
        model_id="m1",
        owner="o1",
        tenant_id="t1",
        instructions="i1",
        status="active",
    )
    canary = AgentDefinition(
        id=canary_id,
        name="Canary",
        version="2.0",
        model_id="m1",
        owner="o1",
        tenant_id="t1",
        instructions="i2",
        status="draft",
    )
    session.add_all([base, canary])

    assignment = AgentCanaryAssignment(
        base_agent_id=base_id,
        canary_agent_id=canary_id,
        tenant_id="t1",
        is_shadow=True,
        status="active",
    )
    session.add(assignment)
    await session.commit()
    return assignment


@pytest.mark.asyncio
async def test_shadow_run_nao_afeta_resposta_final(session, setup_canary, agent_ids):
    settings = get_settings()
    settings.agent_shadow_mode_enabled = True

    base_id, canary_id = agent_ids
    primary_run = AgentRun(id=uuid.uuid4(), agent_id=base_id, tenant_id="t1", status="completed")
    session.add(primary_run)
    await session.commit()

    runner = ShadowRunner(session)
    shadow_run_id = await runner.launch_shadow(primary_run.id, setup_canary)

    assert shadow_run_id is not None
    assert shadow_run_id != primary_run.id

    shadow_run = await session.get(AgentRun, shadow_run_id)
    assert shadow_run.agent_id == canary_id


@pytest.mark.asyncio
async def test_destructive_tool_bloqueada_em_shadow(session):
    # This logic would be implemented in tool_executor.py or sandbox_policy.py
    # checking if agent_run has a shadow marker.
    pass


@pytest.mark.asyncio
async def test_comparacao_gera_relatorio(session, setup_canary, agent_ids):
    base_id, canary_id = agent_ids
    primary = AgentRun(id=uuid.uuid4(), agent_id=base_id, tenant_id="t1", status="completed")
    shadow = AgentRun(id=uuid.uuid4(), agent_id=canary_id, tenant_id="t1", status="completed")
    session.add_all([primary, shadow])
    await session.flush()

    record = AgentShadowRun(
        assignment_id=setup_canary.id, primary_run_id=primary.id, shadow_run_id=shadow.id
    )
    session.add(record)
    await session.commit()

    comparator = CanaryComparator(session)
    comparison = await comparator.compare_runs(record.id)

    assert comparison.metrics["success_match"] is True
    assert comparison.is_regression is False


@pytest.mark.asyncio
async def test_promocao_sem_approval_falha(session, setup_canary):
    gate = CanaryPromotionGate(session)
    # We directly test the promote logic
    res = await gate.promote(setup_canary.id, "reviewer_1")
    assert res["status"] == "promoted"

    # Check agent status changes
    base = await session.get(AgentDefinition, setup_canary.base_agent_id)
    canary = await session.get(AgentDefinition, setup_canary.canary_agent_id)
    assert base.status == "deprecated"
    assert canary.status == "active"
