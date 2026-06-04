import uuid

import pytest
from app.models.agents import AgentPlan, AgentTask, AgentTaskDependency
from app.services.agents import agent_state
from app.services.agents.agent_planner import AgentPlanner
from app.services.agents.task_engine import TaskEngine
from sqlalchemy.future import select


@pytest.mark.asyncio
async def test_create_plan_and_dependencies(session):
    # Setup
    agent_id = uuid.uuid4()
    run = await agent_state.create_agent_run(session, agent_id, "t1", "goal")
    
    planner = AgentPlanner(session)
    tasks_data = [
        {"title": "Task 1", "task_type": "tool_call", "ref": "t1"},
        {"title": "Task 2", "task_type": "tool_call", "ref": "t2", "dependencies": ["t1"]}
    ]
    
    plan = await planner.create_plan(run.id, "my goal", tasks_data)
    
    assert plan.status == "draft"
    
    # Check tasks via select to avoid lazy load issues in tests
    res_tasks = await session.execute(select(AgentTask).where(AgentTask.plan_id == plan.id))
    tasks = res_tasks.scalars().all()
    assert len(tasks) == 2
    
    # Check dependencies
    res = await session.execute(select(AgentTaskDependency))
    deps = res.scalars().all()
    assert len(deps) == 1

@pytest.mark.asyncio
async def test_task_execution_order(session):
    from app.core.config import get_settings
    settings = get_settings()
    settings.agent_plan_execution_enabled = True
    
    agent_id = uuid.uuid4()
    run = await agent_state.create_agent_run(session, agent_id, "t1", "goal")
    
    planner = AgentPlanner(session)
    tasks_data = [
        {"title": "Step 1", "ref": 0},
        {"title": "Step 2", "ref": 1, "dependencies": [0]}
    ]
    plan = await planner.create_plan(run.id, "goal", tasks_data)
    
    engine = TaskEngine(session)
    
    # Initially none are ready except Step 1
    ready = await engine._get_ready_tasks(plan.id)
    assert len(ready) == 1
    assert ready[0].title == "Step 1"
    
    # Complete Step 1
    ready[0].status = "completed"
    await session.commit()
    
    # Now Step 2 should be ready
    ready2 = await engine._get_ready_tasks(plan.id)
    assert len(ready2) == 1
    assert ready2[0].title == "Step 2"

@pytest.mark.asyncio
async def test_retry_logic(session):
    from app.core.config import get_settings
    settings = get_settings()
    settings.agent_auto_retry_enabled = True
    settings.agent_plan_execution_enabled = True
    settings.agent_planner_real_execution_enabled = True
    settings.agent_task_mock_mode = False
    settings.agent_task_dry_run_mode = False
    settings.agent_task_simulation_mode = False
    settings.agent_execution_enabled = True
    
    task = AgentTask(
        plan_id=uuid.uuid4(),
        title="Flaky Task",
        description_hash="hash",
        task_type="tool_call",
        status="pending",
        max_attempts=2,
        input_data={"tool_name": "missing_tool", "parameters": {}},
    )
    agent_id = uuid.uuid4()
    from app.models.agents import AgentDefinition
    agent_def = AgentDefinition(
        id=agent_id,
        name="retry-agent",
        version="1.0.0",
        description="retry",
        instructions="retry",
        model_id="mock-model",
        owner="owner",
        status="active",
    )
    session.add(agent_def)
    await session.commit()
    run = await agent_state.create_agent_run(session, agent_id, "t1", "goal")
    plan = AgentPlan(agent_run_id=run.id, goal_hash="h", status="draft")
    session.add(plan)
    await session.flush()
    task.plan_id = plan.id
    session.add(task)
    await session.commit()
    
    engine = TaskEngine(session)
    await engine.run_task(task.id)
    await session.refresh(task)

    assert task.status == "failed"
    assert task.attempt_count == 2
