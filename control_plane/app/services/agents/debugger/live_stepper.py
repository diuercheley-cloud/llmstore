# Owner: agent-platform
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_debugger import AgentDebugSession
from app.services.agents.debugger.debug_sessions import DebugSessionManager
from app.services.agents.debugger.breakpoints import BreakpointManager

logger = logging.getLogger(__name__)

class LiveStepper:
    """
    Handles live stepping logic for agent execution.
    Integrates breakpoints and interactive pause/resume.
    """
    def __init__(self, db: AsyncSession, session_manager: DebugSessionManager, breakpoint_manager: BreakpointManager):
        self.db = db
        self.session_manager = session_manager
        self.breakpoint_manager = breakpoint_manager

    async def check_and_pause(self, run_id: uuid.UUID, tenant_id: str, step_number: int, event_type: str, state: Dict[str, Any], target: Optional[str] = None):
        """
        Called during agent execution to check if we should pause.
        """
        session = await self.session_manager.get_or_create_session(run_id, tenant_id)
        
        # 1. Check if live stepping is enabled for this session
        if session.is_live_stepping:
            await self._pause_and_wait(session, step_number, "live_stepping", state)
            return

        # 2. Check breakpoints
        active_breakpoints = await self.breakpoint_manager.get_breakpoints(run_id)
        if self.breakpoint_manager.should_break(active_breakpoints, event_type, target):
            await self._pause_and_wait(session, step_number, "breakpoint_hit", state, {"breakpoint_type": event_type, "target": target})

    async def _pause_and_wait(self, session: AgentDebugSession, step_number: int, event_type: str, state: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Pauses the execution and waits for a resume/step signal.
        In a real distributed system, this might involve polling or a message queue.
        """
        logger.info(f"Agent execution paused for run {session.run_id} at step {step_number} due to {event_type}")
        
        # Sanitize state before recording
        sanitized_state = self._sanitize_state(state)
        
        await self.session_manager.record_step_event(session.id, step_number, event_type, sanitized_state, metadata)
        await self.session_manager.pause_session(session.id)
        
        # Simulation of waiting for resume: poll DB until status is 'active'
        while True:
            await self.db.refresh(session)
            if session.status == "active":
                break
            await asyncio.sleep(1) # Wait for human/API intervention
            
        logger.info(f"Agent execution resumed for run {session.run_id}")

    def _sanitize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Removes secrets and sensitive CoT from the state snapshot.
        """
        # Simplistic sanitization
        sanitized = dict(state)
        if "chain_of_thought" in sanitized:
            sanitized["chain_of_thought"] = "[REDACTED FOR DEBUG]"
        
        # Deep scrub for secrets
        self._deep_scrub(sanitized)
        return sanitized

    def _deep_scrub(self, data: Any):
        if isinstance(data, dict):
            for k in list(data.keys()):
                if any(secret in k.lower() for secret in ["api_key", "secret", "password", "token"]):
                    data[k] = "[REDACTED]"
                else:
                    self._deep_scrub(data[k])
        elif isinstance(data, list):
            for item in data:
                self._deep_scrub(item)
