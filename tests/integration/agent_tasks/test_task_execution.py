import uuid
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.models.agents.agent_workflows import AgentWorkflow, AgentWorkflowRun, AgentWorkflowSignal
from app.models.agents.agents import (
    AgentApprovalRequest,
    AgentDefinition,
    AgentHandoffEvent,
    AgentHandoffPolicy,
    AgentMemoryConsent,
    AgentMemoryItem,
    AgentMemoryPolicy,
    AgentPlan,
    AgentRunReceipt,
    AgentRunStep,
    AgentTask,
    AgentTaskAttempt,
    AgentTool,
)
from app.services.agents import agent_state
from app.services.agents.agent_llm_provider import MockAgentLLMProvider
from app.services.agents.task_engine import TaskEngine
from sqlalchemy import select


@pytest.fixture(autouse=True)
def task_engine_settings():
    settings = get_settings()
    original = {
        "agent_plan_execution_enabled": settings.agent_plan_execution_enabled,
        "agent_planner_real_execution_enabled": settings.agent_planner_real_execution_enabled,
        "agent_task_mock_mode": settings.agent_task_mock_mode,
        "agent_task_dry_run_mode": settings.agent_task_dry_run_mode,
        "agent_task_simulation_mode": settings.agent_task_simulation_mode,
        "agent_execution_enabled": settings.agent_execution_enabled,
        "agent_memory_enabled": settings.agent_memory_enabled,
        "agent_memory_write_enabled": settings.agent_memory_write_enabled,
        "agent_long_term_memory_enabled": settings.agent_long_term_memory_enabled,
        "agent_memory_consent_required": settings.agent_memory_consent_required,
        "agent_handoffs_enabled": settings.agent_handoffs_enabled,
        "agent_human_approval_enabled": settings.agent_human_approval_enabled,
        "agent_approval_required_for_high_risk": settings.agent_approval_required_for_high_risk,
        "agent_auto_retry_enabled": settings.agent_auto_retry_enabled,
    }
    settings.agent_plan_execution_enabled = True
    settings.agent_planner_real_execution_enabled = True
    settings.agent_task_mock_mode = False
    settings.agent_task_dry_run_mode = False
    settings.agent_task_simulation_mode = False
    settings.agent_execution_enabled = True
    settings.agent_memory_enabled = False
    settings.agent_memory_write_enabled = False
    settings.agent_long_term_memory_enabled = False
    settings.agent_memory_consent_required = True
    settings.agent_handoffs_enabled = False
    settings.agent_human_approval_enabled = True
    settings.agent_approval_required_for_high_risk = True
    settings.agent_auto_retry_enabled = True
    yield settings
    for key, value in original.items():
        setattr(settings, key, value)


async def _create_agent_run_plan(session, *, allowed_tools=None, tenant_id="tenant-a"):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="task-agent",
        version="1.0.0",
        description="test",
        instructions="test instructions",
        model_id="mock-model",
        owner="tester",
        tenant_id=tenant_id,
        allowed_tools=allowed_tools or [],
        status="active",
        risk_level="medium",
    )
    session.add(agent)
    await session.commit()

    run = await agent_state.create_agent_run(session, agent.id, tenant_id, "goal")
    run.status = "running"
    plan = AgentPlan(agent_run_id=run.id, goal_hash="goal-hash", status="executing")
    session.add(plan)
    await session.commit()
    return agent, run, plan


async def _create_task(session, plan, task_type, input_data):
    task = AgentTask(
        plan_id=plan.id,
        title=f"{task_type} task",
        description_hash="desc-hash",
        task_type=task_type,
        status="pending",
        input_data=input_data,
        max_attempts=2,
    )
    session.add(task)
    await session.commit()
    return task


async def _assert_completed_artifacts(session, run_id, task_id):
    task = await session.get(AgentTask, task_id)
    assert task.status == "completed"
    assert task.output_data["execution_mode"] == "real"
    assert task.output_data["receipt_id"]
    assert task.output_data["output_hash"]

    receipts = (
        (
            await session.execute(
                select(AgentRunReceipt)
                .where(AgentRunReceipt.run_id == run_id)
                .order_by(AgentRunReceipt.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert receipts

    steps = (
        (
            await session.execute(
                select(AgentRunStep)
                .where(AgentRunStep.run_id == run_id)
                .order_by(AgentRunStep.step_number.asc())
            )
        )
        .scalars()
        .all()
    )
    assert steps
    assert steps[-1].status == "success"


@pytest.mark.asyncio
async def test_model_reasoning_chama_agent_llm_provider(session):
    agent, run, plan = await _create_agent_run_plan(session)
    task = await _create_task(
        session,
        plan,
        "model_reasoning",
        {"prompt": "Summarize incident", "allowed_tools": []},
    )
    provider = MockAgentLLMProvider(
        responses=[
            {
                "type": "final",
                "output": "reasoned answer",
                "usage": {"prompt_tokens": 5, "completion_tokens": 7},
                "cost_brl": 0.12,
            }
        ]
    )

    engine = TaskEngine(session, llm_provider=provider)
    await engine.run_task(task.id)

    await session.refresh(run)
    assert run.total_tokens == 12
    assert run.estimated_cost_brl == pytest.approx(0.12)
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_tool_call_chama_tool_executor(session):
    agent, run, plan = await _create_agent_run_plan(session, allowed_tools=["echo_tool"])
    session.add(
        AgentTool(
            name="echo_tool",
            version="1.0.0",
            description="echo",
            category="filesystem_safe",
            input_schema_json={"type": "object"},
            output_schema_json={"type": "object"},
            side_effect_level="none",
            enabled=True,
            owner="tester",
        )
    )
    await session.commit()
    task = await _create_task(
        session,
        plan,
        "tool_call",
        {"tool_name": "echo_tool", "parameters": {"value": "hello"}},
    )

    calls = []

    async def fake_tool_executor(**kwargs):
        calls.append(kwargs)
        return {"echo": kwargs["parameters"]["value"]}

    engine = TaskEngine(session, tool_executor=fake_tool_executor)
    await engine.run_task(task.id)

    await session.refresh(run)
    assert len(calls) == 1
    assert run.tool_calls_count == 1
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_memory_read_chama_agent_memory(session, task_engine_settings):
    task_engine_settings.agent_memory_enabled = True
    agent, run, plan = await _create_agent_run_plan(session)
    session.add(
        AgentMemoryPolicy(
            tenant_id=run.tenant_id,
            agent_id=agent.id,
            memory_type="short_term",
            retention_days=7,
            redaction_enabled=False,
        )
    )
    await session.commit()
    memory_item = AgentMemoryItem(
        tenant_id=run.tenant_id,
        agent_id=agent.id,
        memory_type="short_term",
        content_hash="hash",
        raw_content="stored memory",
        summary="stored summary",
        provenance={},
        retention_until=run.started_at + timedelta(days=1),
    )
    session.add(memory_item)
    await session.commit()
    task = await _create_task(
        session,
        plan,
        "memory_read",
        {"memory_type": "short_term", "limit": 5},
    )

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    await session.refresh(run)
    assert run.memory_reads_count == 1
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_memory_write_respeita_consent_e_policy(session, task_engine_settings):
    import unittest.mock

    task_engine_settings.agent_memory_enabled = True
    task_engine_settings.agent_memory_write_enabled = True
    task_engine_settings.agent_long_term_memory_enabled = True
    agent, run, plan = await _create_agent_run_plan(session)
    session.add(
        AgentMemoryPolicy(
            tenant_id=run.tenant_id,
            agent_id=agent.id,
            memory_type="long_term",
            retention_days=30,
            redaction_enabled=False,
        )
    )
    session.add(
        AgentMemoryConsent(
            tenant_id=run.tenant_id,
            user_id="user-1",
            memory_type="long_term",
            agent_id=agent.id,
            status="active",
        )
    )
    await session.commit()
    task = await _create_task(
        session,
        plan,
        "memory_write",
        {
            "memory_type": "long_term",
            "content": "customer preference",
            "summary": "preference",
            "user_id": "user-1",
        },
    )

    # Mock the indexing service to prevent PGVector syntax errors on SQLite
    with unittest.mock.patch(
        "app.services.agents.memory_indexing.MemoryIndexingService.index_item", return_value=None
    ):
        engine = TaskEngine(session)
        await engine.run_task(task.id)

    items = (
        (
            await session.execute(
                select(AgentMemoryItem).where(AgentMemoryItem.source_run_id == run.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(items) == 1
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_approval_wait_pausa_run(session):
    agent, run, plan = await _create_agent_run_plan(session, allowed_tools=["dangerous_tool"])
    session.add(
        AgentTool(
            name="dangerous_tool",
            version="1.0.0",
            description="danger",
            category="filesystem_destructive",
            input_schema_json={"type": "object"},
            output_schema_json={"type": "object"},
            risk_level="high",
            side_effect_level="destructive",
            requires_approval=True,
            enabled=True,
            owner="tester",
        )
    )
    await session.commit()
    task = await _create_task(
        session,
        plan,
        "approval_wait",
        {"tool_name": "dangerous_tool", "parameters": {"target": "resource-1"}},
    )

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    await session.refresh(run)
    await session.refresh(plan)
    await session.refresh(task)
    assert run.status == "waiting_approval"
    assert plan.status == "waiting_approval"
    assert task.status == "waiting_approval"
    approval = (
        await session.execute(
            select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == run.id)
        )
    ).scalar_one_or_none()
    assert approval is not None
    assert task.output_data["receipt_id"]
    assert task.output_data["output_hash"]


@pytest.mark.asyncio
async def test_handoff_chama_agent_handoffs(session, task_engine_settings):
    task_engine_settings.agent_handoffs_enabled = True
    source_agent, run, plan = await _create_agent_run_plan(session)
    target_agent = AgentDefinition(
        id=uuid.uuid4(),
        name="target-agent",
        version="1.0.0",
        description="target",
        instructions="target instructions",
        model_id="mock-model",
        owner="tester",
        tenant_id=run.tenant_id,
        status="active",
        risk_level="medium",
    )
    session.add(target_agent)
    await session.commit()
    session.add(
        AgentHandoffPolicy(
            tenant_id=run.tenant_id,
            source_agent_id=source_agent.id,
            target_agent_id=target_agent.id,
            max_handoffs_per_run=2,
        )
    )
    await session.commit()
    task = await _create_task(
        session,
        plan,
        "handoff",
        {
            "target_agent_id": str(target_agent.id),
            "reason": "Need specialist",
            "context": {"ticket_id": "inc-1"},
        },
    )

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    handoff = (
        await session.execute(
            select(AgentHandoffEvent).where(AgentHandoffEvent.source_run_id == run.id)
        )
    ).scalar_one_or_none()
    assert handoff is not None
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_workflow_signal_envia_signal(session):
    agent, run, plan = await _create_agent_run_plan(session)
    workflow = AgentWorkflow(
        tenant_id=run.tenant_id,
        name="wf",
        version="1.0.0",
        status="created",
        input_data={},
    )
    session.add(workflow)
    await session.commit()
    workflow_run = AgentWorkflowRun(
        workflow_id=workflow.id,
        tenant_id=run.tenant_id,
        status="waiting_signal",
        current_state="wait",
        state_data={},
        context={},
    )
    session.add(workflow_run)
    await session.commit()
    task = await _create_task(
        session,
        plan,
        "workflow_signal",
        {"workflow_run_id": str(workflow_run.id), "signal_name": "resume", "payload": {"ok": True}},
    )

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    signal = (
        await session.execute(
            select(AgentWorkflowSignal).where(AgentWorkflowSignal.run_id == workflow_run.id)
        )
    ).scalar_one_or_none()
    assert signal is not None
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_final_response_conclui_run(session):
    agent, run, plan = await _create_agent_run_plan(session)
    task = await _create_task(
        session,
        plan,
        "final_response",
        {"output": {"answer": "done"}, "metadata": {"channel": "api"}},
    )

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    await session.refresh(run)
    await session.refresh(plan)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.output_hash is not None
    assert plan.status == "completed"
    await _assert_completed_artifacts(session, run.id, task.id)


@pytest.mark.asyncio
async def test_task_sem_executor_falha_sem_completed(session):
    _, run, plan = await _create_agent_run_plan(session)
    task = await _create_task(session, plan, "unknown_task", {"value": 1})

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    await session.refresh(task)
    assert task.status == "failed"
    assert task.output_data["error_code"] == "unsupported_task_type"
    attempt = (
        await session.execute(select(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task.id))
    ).scalar_one()
    assert attempt.status == "failed"


@pytest.mark.asyncio
async def test_not_implemented_nao_aparece_em_modo_real(session, task_engine_settings):
    task_engine_settings.agent_task_simulation_mode = True
    _, _, plan = await _create_agent_run_plan(session)
    task = await _create_task(
        session, plan, "tool_call", {"tool_name": "missing", "parameters": {}}
    )

    engine = TaskEngine(session)
    await engine.run_task(task.id)

    attempt = (
        await session.execute(select(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task.id))
    ).scalar_one()
    assert attempt.status == "failed"
    assert "NotImplementedError" not in (attempt.error or "")
    assert "controlled_not_implemented" not in (attempt.error or "")
