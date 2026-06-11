import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.session
from app.db.base import Base
from app.models.agents.agents import AgentDefinition, AgentRun, AgentRunStep
from app.services.agents.agent_executor import AgentExecutor, MockLLMProvider
from app.services.agents.simulation import SimulationRuntime
from app.core.config import get_settings

TEST_DB_FILE = Path("/tmp/test-agent-simulation.db")

@pytest_asyncio.fixture(autouse=True)
async def test_db():
    db_url = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield session_factory
    
    await engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass

@pytest_asyncio.fixture(autouse=True)
async def setup_settings():
    settings = get_settings()
    orig_obs = settings.agent_observability_enabled
    orig_sandbox = settings.agent_tool_sandbox_enabled
    orig_exec = settings.agent_execution_enabled
    orig_tool_exec = settings.agent_tool_execution_enabled
    orig_executor_mock = settings.agent_executor_mock_mode
    
    settings.agent_observability_enabled = True
    settings.agent_tool_sandbox_enabled = False
    settings.agent_execution_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_executor_mock_mode = False
    
    yield
    
    settings.agent_observability_enabled = orig_obs
    settings.agent_tool_sandbox_enabled = orig_sandbox
    settings.agent_execution_enabled = orig_exec
    settings.agent_tool_execution_enabled = orig_tool_exec
    settings.agent_executor_mock_mode = orig_executor_mock

def test_tool_classification():
    # Email
    assert SimulationRuntime.classify_tool("send_email") == "email"
    assert SimulationRuntime.classify_tool("smtp_send") == "email"
    assert SimulationRuntime.classify_tool("custom_tool", "email") == "email"

    # Filesystem
    assert SimulationRuntime.classify_tool("write_file") == "filesystem"
    assert SimulationRuntime.classify_tool("delete_directory") == "filesystem"
    assert SimulationRuntime.classify_tool("custom_tool", "filesystem_safe") == "filesystem"

    # Shell
    assert SimulationRuntime.classify_tool("run_bash") == "shell"
    assert SimulationRuntime.classify_tool("execute_cmd") == "shell"
    assert SimulationRuntime.classify_tool("custom_tool", "shell_command") == "shell"

    # APIs
    assert SimulationRuntime.classify_tool("fetch_api_data") == "APIs"
    assert SimulationRuntime.classify_tool("send_http_request") == "APIs"
    assert SimulationRuntime.classify_tool("custom_tool", "external_api") == "APIs"

    # Database writes
    assert SimulationRuntime.classify_tool("db_write_record") == "database writes"
    assert SimulationRuntime.classify_tool("insert_record") == "database writes"
    assert SimulationRuntime.classify_tool("custom_tool", "database_write") == "database writes"

    # Other
    assert SimulationRuntime.classify_tool("read_only_tool", "database_read") == "other"

def test_simulated_outputs():
    # Email
    out_email = SimulationRuntime.simulate_tool_execution("send_email", "email", {"to": "user@test.com", "subject": "Hello"})
    assert out_email["status"] == "success"
    assert "Email successfully sent" in out_email["message"]
    assert out_email["simulated"] is True

    # Filesystem
    out_fs = SimulationRuntime.simulate_tool_execution("write_file", "filesystem", {"path": "/tmp/test.txt", "content": "data"})
    assert out_fs["status"] == "success"
    assert "Simulated filesystem operation" in out_fs["message"]
    assert out_fs["simulated"] is True

    # Shell
    out_shell = SimulationRuntime.simulate_tool_execution("run_bash", "shell", {"cmd": "ls"})
    assert out_shell["status"] == "success"
    assert out_shell["exit_code"] == 0
    assert "Simulated command execution" in out_shell["stdout"]
    assert out_shell["simulated"] is True

    # APIs
    out_api = SimulationRuntime.simulate_tool_execution("fetch_api", "APIs", {"url": "https://api.com"})
    assert out_api["status"] == "success"
    assert out_api["status_code"] == 200
    assert out_api["simulated"] is True

    # Database
    out_db = SimulationRuntime.simulate_tool_execution("db_write", "database writes", {"query": "UPDATE"})
    assert out_db["status"] == "success"
    assert out_db["rows_affected"] == 1
    assert out_db["simulated"] is True

@pytest.mark.asyncio
async def test_agent_run_simulation_interception(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(), name="Simulation Agent", tenant_id="t1", status="active",
            instructions="Test", model_id="gpt-4", owner="admin", version="1.0.0"
        )
        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running",
            input_text="Run test", total_steps=0, total_tokens=0, estimated_cost_brl=0.0,
            is_simulation=True
        )
        db.add(agent)
        db.add(run)
        
        # Add a tool to DB to pass tool resolution check
        from app.models.agents.agents import AgentTool
        tool = AgentTool(
            id=uuid.uuid4(), name="write_file", description="FS Write",
            category="filesystem_safe", input_schema_json={}, output_schema_json={},
            enabled=True
        )
        db.add(tool)
        await db.commit()

        # Mock LLM to return tool_call decision
        mock_llm = MockLLMProvider([
            {"type": "tool_call", "tool_name": "write_file", "tool_input": {"path": "/var/log/app.log", "content": "Log entry"}}
        ])
        
        executor = AgentExecutor(db, run.id, llm_provider=mock_llm)
        
        # Execute tool call step
        await executor.execute_step()
        await db.commit()

        # Verify step logged in DB contains simulation metadata
        stmt = select(AgentRunStep).where(AgentRunStep.run_id == run.id, AgentRunStep.step_type == "tool_call")
        res = await db.execute(stmt)
        step = res.scalar_one_or_none()
        
        assert step is not None
        assert step.step_metadata is not None
        assert step.step_metadata.get("simulated") is True
        assert step.step_metadata.get("simulation_category") == "filesystem"
        assert step.step_metadata.get("tool_name") == "write_file"

        # Generate report
        report = await SimulationRuntime.generate_simulation_report(db, run.id)
        
        assert report["status"] == "success"
        assert report["summary"]["total_intercepted"] == 1
        assert report["summary"]["categories"]["filesystem"] == 1
        assert len(report["intercepted_actions"]) == 1
        assert report["intercepted_actions"][0]["tool_name"] == "write_file"
        assert report["intercepted_actions"][0]["category"] == "filesystem"
        
        # Reload run and check report column
        await db.refresh(run)
        assert run.simulation_report is not None
        assert run.simulation_report["summary"]["total_intercepted"] == 1
