# Owner: agent-platform
import logging
from enum import Enum
from typing import Any, Dict, Optional

from app.core.time import utc_now
from app.models.agents.agent_workflows import AgentWorkflowEvent, AgentWorkflowRun

logger = logging.getLogger(__name__)

class WorkflowStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SLEEPING = "sleeping"
    WAITING_SIGNAL = "waiting_signal"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_WEBHOOK = "waiting_webhook"
    RETRY_SCHEDULED = "retry_scheduled"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATED = "compensated"

class WorkflowStateMachine:
    """
    Handles state transitions and persistence for Agent Workflows.
    Ensures that every transition is logged and the run state is updated.
    """
    
    def __init__(self, run: AgentWorkflowRun):
        self.run = run

    async def transition_to(self, to_status: WorkflowStatus, payload: Optional[Dict[str, Any]] = None):
        """
        Performs a status transition, updating the run and recording an event.
        """
        from_status = self.run.status
        logger.info(f"Workflow {self.run.id} transitioning status from {from_status} to {to_status}")
        
        self.run.status = to_status.value
        self.run.updated_at = utc_now()
        
        event = AgentWorkflowEvent(
            run_id=self.run.id,
            event_type="status_transition",
            from_state=from_status,
            to_state=to_status.value,
            payload=payload or {},
            created_at=utc_now()
        )
        return event

    def set_current_state(self, state_name: str):
        """
        Updates the logical current state of the workflow.
        """
        previous_state = self.run.current_state
        self.run.current_state = state_name
        self.run.updated_at = utc_now()
        return AgentWorkflowEvent(
            run_id=self.run.id,
            event_type="state_handoff",
            from_state=previous_state,
            to_state=state_name,
            payload={"state_name": state_name},
            created_at=utc_now(),
        )

    def update_context(self, updates: Dict[str, Any]):
        """
        Updates the workflow run context.
        """
        current = dict(self.run.context or {})
        current.update(updates)
        self.run.context = current
        self.run.updated_at = utc_now()

    def get_context(self) -> Dict[str, Any]:
        return self.run.context or {}

    def update_state_data(self, updates: Dict[str, Any]):
        current = dict(self.run.state_data or {})
        current.update(updates)
        self.run.state_data = current
        self.run.updated_at = utc_now()
