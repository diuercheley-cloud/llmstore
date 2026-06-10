# Owner: agent-platform
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.models.agents.agent_debugger import AgentBreakpoint, AgentDebugSession
from app.services.agents.debugger.breakpoints import BreakpointManager
from app.services.agents.debugger.debug_sessions import DebugSessionManager
from app.services.agents.debugger.live_stepper import LiveStepper
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    db = MagicMock(spec=AsyncSession)
    # Mock refresh to avoid actual DB call in _pause_and_wait loop
    db.refresh = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_breakpoint_hit_pauses(mock_db):
    run_id = uuid.uuid4()
    tenant_id = "tenant_1"
    
    session_manager = DebugSessionManager(mock_db)
    bp_manager = BreakpointManager(mock_db)
    stepper = LiveStepper(mock_db, session_manager, bp_manager)
    
    # 1. Mock session and breakpoints
    session = AgentDebugSession(id=uuid.uuid4(), run_id=run_id, status="paused")
    session_manager.get_or_create_session = AsyncMock(return_value=session)
    
    bp = AgentBreakpoint(type="tool_name", target="search_web")
    bp_manager.get_breakpoints = AsyncMock(return_value=[bp])
    
    # Mock record_step_event and pause_session
    session_manager.record_step_event = AsyncMock()
    session_manager.pause_session = AsyncMock()
    
    # 2. Simulate hitting a breakpoint
    # We use a task to run check_and_pause because it loop/waits
    task = asyncio.create_task(stepper.check_and_pause(
        run_id, tenant_id, 1, "tool_name", {"password": "secret_password"}, target="search_web"
    ))
    
    # Allow some time for the task to reach the pause loop
    await asyncio.sleep(0.1)
    
    # Verify it attempted to pause
    session_manager.record_step_event.assert_called()
    session_manager.pause_session.assert_called()
    
    # Verify sanitization in recorded event
    args, _ = session_manager.record_step_event.call_args
    recorded_state = args[3]
    assert recorded_state["password"] == "[REDACTED]"
    
    # 3. Simulate resume from another "process"
    session.status = "active"
    
    # Wait for task to finish
    await task
    assert task.done()

@pytest.mark.asyncio
async def test_sanitization_secrets():
    stepper = LiveStepper(None, None, None)
    state = {
        "config": {"api_key": "12345", "other": "val"},
        "nested": [{"password": "abc"}, {"safe": "ok"}],
        "chain_of_thought": "I will search for the secret"
    }
    
    sanitized = stepper._sanitize_state(state)
    
    assert sanitized["config"]["api_key"] == "[REDACTED]"
    assert sanitized["config"]["other"] == "val"
    assert sanitized["nested"][0]["password"] == "[REDACTED]"
    assert sanitized["nested"][1]["safe"] == "ok"
    assert sanitized["chain_of_thought"] == "[REDACTED FOR DEBUG]"
