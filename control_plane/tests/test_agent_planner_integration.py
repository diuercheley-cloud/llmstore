import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents import AgentDefinition, AgentRun, AgentTask
from app.services.agents.agent_planner import AgentPlanner
from app.services.agents.task_engine import TaskEngine
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_task_engine_real_execution_tool_call(db_session: AsyncSession):
    settings = get_settings()
    settings.agent_plan_execution_enabled = True
    settings.agent_planner_real_execution_enabled = True
    
    # Create agent and run
    agent = AgentDefinition(
        id=uuid.uuid4(), name="test-agent", version="1.0.0", instructions="test", model_id="test-model", owner="test"
    )
    db_session.add(agent)
    run = AgentRun(id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running", input_text="test")
    db_session.add(run)
    await db_session.commit()
    
    # Create plan and task
    planner = AgentPlanner(db_session)
    tasks_data = [{
        "title": "fetch_data",
        "task_type": "tool_call",
        "input_data": {"tool_name": "echo_tool", "parameters": {"message": "hello"}}
    }]
    plan = await planner.create_plan(run.id, "test goal", tasks_data)
    plan.status = "executing"
    await db_session.commit()
    
    # Mock execute_tool
    with patch("app.services.agents.task_engine.execute_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"echo": "hello"}
        
        engine = TaskEngine(db_session)
        await engine.execute_plan(plan.id)
        
        # Verify execution
        res_task = await db_session.execute(select(AgentTask).where(AgentTask.plan_id == plan.id))
        task = res_task.scalar_one()
        assert task.status == "completed"
        assert task.output_data == {"echo": "hello"}
        mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_task_dependency_blocking(db_session: AsyncSession):
    settings = get_settings()
    settings.agent_plan_execution_enabled = True
    
    run_id = uuid.uuid4()
    # Mock run and agent... (omitted for brevity in this manual check)
    
    planner = AgentPlanner(db_session)
    tasks_data = [
        {"title": "task1", "ref": "t1"},
        {"title": "task2", "dependencies": ["t1"]}
    ]
    # We'll just check if _get_ready_tasks works as expected
    plan = await planner.create_plan(uuid.uuid4(), "goal", tasks_data)
    
    engine = TaskEngine(db_session)
    ready = await engine._get_ready_tasks(plan.id)
    
    assert len(ready) == 1
    assert ready[0].title == "task1"


from sqlalchemy import select
