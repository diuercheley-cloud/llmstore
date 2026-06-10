import uuid

import pytest
from app.core.config import get_settings
from app.models.agents.agents import AgentDefinition, AgentRunStep, AgentTool
from app.services.agents import agent_state
from app.services.agents.agent_executor import AgentExecutor
from app.services.agents.agent_readiness import AgentReadinessService
from sqlalchemy import select


@pytest.fixture(autouse=True)
def executor_governance_settings():
    settings = get_settings()
    original = {
        "agent_runtime_enabled": settings.agent_runtime_enabled,
        "agent_execution_plane_enabled": settings.agent_execution_plane_enabled,
        "agent_execution_enabled": settings.agent_execution_enabled,
        "agent_tool_execution_enabled": settings.agent_tool_execution_enabled,
        "agent_observability_enabled": settings.agent_observability_enabled,
        "agent_executor_mock_mode": settings.agent_executor_mock_mode,
        "agent_executor_dry_run_mode": settings.agent_executor_dry_run_mode,
        "agent_executor_allow_simulation": settings.agent_executor_allow_simulation,
        "deployment_mode": settings.deployment_mode,
    }
    settings.agent_runtime_enabled = True
    settings.agent_execution_plane_enabled = True
    settings.agent_execution_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_observability_enabled = True
    settings.agent_executor_mock_mode = False
    settings.agent_executor_dry_run_mode = False
    settings.agent_executor_allow_simulation = False
    settings.deployment_mode = "appliance"
    yield settings
    for key, value in original.items():
        setattr(settings, key, value)


async def _create_run_with_tool(session):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="exec-agent",
        version="1.0.0",
        description="test",
        instructions="test",
        model_id="gateway-model",
        owner="tester",
        tenant_id="tenant-exec",
        status="active",
        allowed_tools=["echo_tool"],
    )
    tool = AgentTool(
        id=uuid.uuid4(),
        name="echo_tool",
        version="1.0.0",
        description="echo",
        category="filesystem_safe",
        input_schema_json={"type": "object"},
        output_schema_json={"type": "object"},
        enabled=True,
        owner="tester",
    )
    session.add_all([agent, tool])
    await session.commit()
    run = await agent_state.create_agent_run(session, agent.id, "tenant-exec", "hello")
    run.status = "running"
    await session.commit()
    return run


@pytest.mark.asyncio
async def test_simulation_disabled_bloqueia_caminho_simulado(session, executor_governance_settings):
    executor_governance_settings.agent_execution_enabled = False
    run = await _create_run_with_tool(session)
    executor = AgentExecutor(session, run.id)

    should_continue = await executor._execute_tool_and_process(run, "echo_tool", {"msg": "hi"}, 1)

    await session.refresh(run)
    assert should_continue is False
    assert run.status == "failed"
    assert "Agent execution is disabled" in run.failure_reason


@pytest.mark.asyncio
async def test_mock_enabled_funciona_e_fica_marcado(session, executor_governance_settings):
    executor_governance_settings.agent_executor_mock_mode = True
    run = await _create_run_with_tool(session)
    executor = AgentExecutor(session, run.id)

    output = executor._build_simulated_output(
        mode="mock",
        tool_name="echo_tool",
        reason="AGENT_EXECUTOR_MOCK_MODE=true",
        policy_decision_id=None,
    )
    should_continue = await executor._execute_tool_and_process(run, "echo_tool", {"msg": "hi"}, 1)

    assert should_continue is True
    assert output["execution_mode"] == "mock"
    assert output["simulated"] is True
    assert output["reason"] == "AGENT_EXECUTOR_MOCK_MODE=true"


@pytest.mark.asyncio
async def test_production_com_mock_falha_readiness(session, executor_governance_settings):
    executor_governance_settings.deployment_mode = "production"
    executor_governance_settings.agent_executor_mock_mode = True

    readiness = await AgentReadinessService(session).check_readiness()

    check = next(c for c in readiness["checks"] if c["id"] == "executor_modes")
    assert check["status"] == "fail"
    assert "mock" in check["value"]["active_modes"]
    assert readiness["status"] in {"blocked", "degraded"}


@pytest.mark.asyncio
async def test_erro_real_nao_vira_sucesso_simulado(session, executor_governance_settings):
    run = await _create_run_with_tool(session)

    async def failing_tool(name, inputs):
        raise ValueError("tool exploded")

    executor = AgentExecutor(session, run.id, tool_runner=failing_tool)
    should_continue = await executor._execute_tool_and_process(run, "echo_tool", {"msg": "hi"}, 1)

    await session.refresh(run)
    assert should_continue is False
    assert run.status == "failed"

    step = (
        await session.execute(
            select(AgentRunStep).where(AgentRunStep.run_id == run.id).order_by(AgentRunStep.step_number.desc())
        )
    ).scalar_one()
    assert step.status == "failed"
    assert "tool exploded" in (step.error or "")


@pytest.mark.asyncio
async def test_output_simulado_sempre_tem_simulated_true(session, executor_governance_settings):
    executor_governance_settings.agent_executor_mock_mode = True
    run = await _create_run_with_tool(session)
    executor = AgentExecutor(session, run.id)

    mock_output = executor._build_simulated_output(
        mode="mock",
        tool_name="echo_tool",
        reason="mock enabled",
        policy_decision_id="p-1",
    )
    executor_governance_settings.agent_executor_mock_mode = False
    executor_governance_settings.agent_executor_allow_simulation = True
    simulation_output = executor._build_simulated_output(
        mode="simulation",
        tool_name="echo_tool",
        reason="simulation enabled",
        policy_decision_id="p-2",
    )

    assert mock_output["simulated"] is True
    assert simulation_output["simulated"] is True
    assert mock_output["policy_decision_id"] == "p-1"
    assert simulation_output["policy_decision_id"] == "p-2"


@pytest.mark.asyncio
async def test_simulation_flag_nao_substitui_execucao_real(session, executor_governance_settings):
    executor_governance_settings.agent_execution_enabled = True
    executor_governance_settings.agent_executor_allow_simulation = True
    run = await _create_run_with_tool(session)

    async def real_tool(name, inputs):
        return {"echo": inputs["msg"]}

    executor = AgentExecutor(session, run.id, tool_runner=real_tool)
    assert executor._resolve_executor_tool_mode() == "real"
    should_continue = await executor._execute_tool_and_process(run, "echo_tool", {"msg": "hi"}, 1)

    assert should_continue is True
    step = (
        await session.execute(
            select(AgentRunStep).where(AgentRunStep.run_id == run.id).order_by(AgentRunStep.step_number.desc())
        )
    ).scalar_one()
    assert step.status == "success"
