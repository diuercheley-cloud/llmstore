import pytest
import uuid
import json
from sqlalchemy.future import select

from app.models.agents import AgentPlan, AgentTask, AgentTaskAttempt
from app.services.agents import agent_state
from app.services.agents.task_engine import TaskEngine
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_task_sem_executor_nao_vira_completed(session):
    settings = get_settings()
    settings.agent_task_mock_mode = False
    settings.agent_task_dry_run_mode = False
    settings.agent_task_simulation_mode = False
    settings.agent_planner_real_execution_enabled = False # no real execution
    settings.agent_plan_execution_enabled = True
    




    agent_id = uuid.uuid4()
    # Mock an agent definition so policy engine passes
    from app.models.agents import AgentDefinition
    agent_def = AgentDefinition(
        id=agent_id,
        name="test_agent",
        version="1.0",
        description="test",
        instructions="test",
        model_id="mock-model",
        owner="test-owner",
        allowed_tools=["some_tool", "test_tool", "task_engine"],
        status="active"
    )
    session.add(agent_def)
    await session.commit()
    run = await agent_state.create_agent_run(session, agent_def.id, "t1", "goal")




    
    plan = AgentPlan(agent_run_id=run.id, goal_hash="hash", status="executing")
    session.add(plan)
    await session.commit()
    
    task = AgentTask(
        plan_id=plan.id,
        title="No Exec",
        description_hash="hash",
        task_type="tool_call",
        status="pending",
        input_data={"tool_name": "some_tool"}
    )
    session.add(task)
    await session.commit()
    
    engine = TaskEngine(session)
    await engine.run_task(task.id)
    
    await session.refresh(task)
    # Since neither real nor mock nor dry_run are enabled, it should fail
    from app.models.agents import AgentTaskAttempt
    res = await session.execute(select(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task.id))
    attempts = res.scalars().all()
    assert attempts[0].status == "failed"
    
@pytest.mark.asyncio
async def test_mock_mode_disabled_bloqueia_placeholder(session):
    settings = get_settings()
    settings.agent_task_mock_mode = False
    settings.agent_task_dry_run_mode = False
    settings.agent_task_simulation_mode = True # tries to simulate but mock/dry_run are false
    settings.agent_plan_execution_enabled = True
    




    agent_id = uuid.uuid4()
    # Mock an agent definition so policy engine passes
    from app.models.agents import AgentDefinition
    agent_def = AgentDefinition(
        id=agent_id,
        name="test_agent",
        version="1.0",
        description="test",
        instructions="test",
        model_id="mock-model",
        owner="test-owner",
        allowed_tools=["some_tool", "test_tool", "task_engine"],
        status="active"
    )
    session.add(agent_def)
    await session.commit()
    run = await agent_state.create_agent_run(session, agent_def.id, "t1", "goal")




    plan = AgentPlan(agent_run_id=run.id, goal_hash="h", status="draft")
    session.add(plan)
    await session.commit()
    
    task = AgentTask(plan_id=plan.id, title="Task", description_hash="h", task_type="tool_call", input_data={})
    session.add(task)
    await session.commit()
    
    engine = TaskEngine(session)
    await engine.run_task(task.id)
    await session.refresh(task)
    
    res = await session.execute(select(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task.id))
    attempts = res.scalars().all()
    
    if task.status != "failed" or (attempts and "controlled_not_implemented" not in str(attempts[0].error)):
        print(f"ATTEMPT ERROR: {attempts[0].error if attempts else 'No attempt'}")
    assert attempts[0].status == "failed"
    assert "controlled_not_implemented" in str(attempts[0].error) if attempts else False

@pytest.mark.asyncio
async def test_mock_mode_enabled_marca_mock_true(session):
    settings = get_settings()
    settings.agent_task_mock_mode = True
    




    agent_id = uuid.uuid4()
    # Mock an agent definition so policy engine passes
    from app.models.agents import AgentDefinition
    agent_def = AgentDefinition(
        id=agent_id,
        name="test_agent",
        version="1.0",
        description="test",
        instructions="test",
        model_id="mock-model",
        owner="test-owner",
        allowed_tools=["some_tool", "test_tool", "task_engine"],
        status="active"
    )
    session.add(agent_def)
    await session.commit()
    run = await agent_state.create_agent_run(session, agent_def.id, "t1", "goal")




    plan = AgentPlan(agent_run_id=run.id, goal_hash="h", status="draft")
    session.add(plan)
    await session.commit()
    
    task = AgentTask(plan_id=plan.id, title="Task", description_hash="h", task_type="tool_call", input_data={})
    session.add(task)
    await session.commit()
    
    engine = TaskEngine(session)
    await engine.run_task(task.id)
    await session.refresh(task)
    
    if task.status == "failed":
        res = await session.execute(select(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task.id))
        attempt = res.scalar_one_or_none()
        print(f"FAILED ATTEMPT ERROR: {attempt.error if attempt else ''}")
        
    assert task.status == "completed"
    assert task.output_data.get("mock") is True
    assert task.output_data.get("execution_mode") == "mock"

@pytest.mark.asyncio
async def test_dry_run_nao_causa_side_effect(session):
    settings = get_settings()
    settings.agent_task_mock_mode = False
    settings.agent_task_dry_run_mode = True
    




    agent_id = uuid.uuid4()
    # Mock an agent definition so policy engine passes
    from app.models.agents import AgentDefinition
    agent_def = AgentDefinition(
        id=agent_id,
        name="test_agent",
        version="1.0",
        description="test",
        instructions="test",
        model_id="mock-model",
        owner="test-owner",
        allowed_tools=["some_tool", "test_tool", "task_engine"],
        status="active"
    )
    session.add(agent_def)
    await session.commit()
    run = await agent_state.create_agent_run(session, agent_def.id, "t1", "goal")




    plan = AgentPlan(agent_run_id=run.id, goal_hash="h", status="draft")
    session.add(plan)
    await session.commit()
    
    task = AgentTask(plan_id=plan.id, title="Task", description_hash="h", task_type="tool_call", input_data={})
    session.add(task)
    await session.commit()
    
    engine = TaskEngine(session)
    await engine.run_task(task.id)
    await session.refresh(task)
    
    if task.status == "failed":
        res = await session.execute(select(AgentTaskAttempt).where(AgentTaskAttempt.task_id == task.id))
        attempt = res.scalar_one_or_none()
        print(f"FAILED ATTEMPT ERROR: {attempt.error if attempt else ''}")
        
    assert task.status == "completed"
    assert task.output_data.get("dry_run") is True
    assert task.output_data.get("execution_mode") == "dry_run"

@pytest.mark.asyncio
async def test_completed_task_exige_receipt_and_output_hash(session):
    settings = get_settings()
    settings.agent_task_mock_mode = True
    




    agent_id = uuid.uuid4()
    # Mock an agent definition so policy engine passes
    from app.models.agents import AgentDefinition
    agent_def = AgentDefinition(
        id=agent_id,
        name="test_agent",
        version="1.0",
        description="test",
        instructions="test",
        model_id="mock-model",
        owner="test-owner",
        allowed_tools=["some_tool", "test_tool", "task_engine"],
        status="active"
    )
    session.add(agent_def)
    await session.commit()
    run = await agent_state.create_agent_run(session, agent_def.id, "t1", "goal")




    plan = AgentPlan(agent_run_id=run.id, goal_hash="h", status="draft")
    session.add(plan)
    await session.commit()
    
    task = AgentTask(plan_id=plan.id, title="Task", description_hash="h", task_type="tool_call", input_data={})
    session.add(task)
    await session.commit()
    
    engine = TaskEngine(session)
    await engine.run_task(task.id)
    await session.refresh(task)
    
    assert task.status == "completed"
    assert "receipt_id" in task.output_data
    assert "output_hash" in task.output_data
