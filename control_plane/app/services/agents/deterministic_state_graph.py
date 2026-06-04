# Owner: agent-platform
import hashlib
import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Formal state machines states definitions
class AgentRunState:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"

    VALID_STATES = {QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED, WAITING_APPROVAL}

    # Versioned transitions dictionary: Version string -> {from_state -> set of to_states}
    TRANSITIONS = {
        "v1.0": {
            QUEUED: {RUNNING, CANCELLED},
            RUNNING: {COMPLETED, FAILED, CANCELLED, PAUSED, WAITING_APPROVAL},
            PAUSED: {RUNNING, CANCELLED},
            WAITING_APPROVAL: {RUNNING, CANCELLED, FAILED},
            COMPLETED: set(),
            FAILED: set(),
            CANCELLED: set(),
        }
    }


class AgentPlanState:
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"

    VALID_STATES = {PENDING, EXECUTING, COMPLETED, FAILED, COMPENSATED}

    TRANSITIONS = {
        "v1.0": {
            PENDING: {EXECUTING, FAILED},
            EXECUTING: {COMPLETED, FAILED},
            FAILED: {COMPENSATED},
            COMPLETED: set(),
            COMPENSATED: set(),
        }
    }


class AgentTaskState:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    VALID_STATES = {PENDING, RUNNING, COMPLETED, FAILED, SKIPPED}

    TRANSITIONS = {
        "v1.0": {
            PENDING: {RUNNING, SKIPPED, FAILED},
            RUNNING: {COMPLETED, FAILED},
            COMPLETED: set(),
            FAILED: set(),
            SKIPPED: set(),
        }
    }


class AgentExecutionJobState:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    VALID_STATES = {PENDING, RUNNING, COMPLETED, FAILED}

    TRANSITIONS = {
        "v1.0": {
            PENDING: {RUNNING, FAILED},
            RUNNING: {COMPLETED, FAILED},
            COMPLETED: set(),
            FAILED: set(),
        }
    }


class WorkflowExecutionState:
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"

    VALID_STATES = {ACTIVE, COMPLETED, FAILED, SUSPENDED}

    TRANSITIONS = {
        "v1.0": {
            ACTIVE: {COMPLETED, FAILED, SUSPENDED},
            SUSPENDED: {ACTIVE, FAILED},
            COMPLETED: set(),
            FAILED: set(),
        }
    }


class DeterministicStateGraph:
    def __init__(self, version: str = "v1.0"):
        self.version = version

    def validate_transition(self, machine_class: Any, from_state: str, to_state: str) -> bool:
        """
        Validates whether a state transition is allowed under the versioned state machine rules.
        """
        if from_state == to_state:
            return True  # Self-transitions are idempotent/no-op

        if from_state not in machine_class.VALID_STATES or to_state not in machine_class.VALID_STATES:
            logger.warning(f"Invalid state referenced: {from_state} or {to_state}")
            return False

        version_rules = machine_class.TRANSITIONS.get(self.version)
        if not version_rules:
            logger.error(f"Version {self.version} not defined for state machine {machine_class.__name__}")
            return False

        allowed_to = version_rules.get(from_state, set())
        if to_state not in allowed_to:
            logger.warning(f"Forbidden transition from '{from_state}' to '{to_state}' in version {self.version}")
            return False

        return True

    @staticmethod
    def calculate_replay_hash(
        state_transitions: List[Dict[str, Any]],
        receipts: List[Dict[str, Any]],
        output_data: Any
    ) -> str:
        """
        Calculates a deterministic cryptographic SHA-256 hash of the execution history,
        state transitions, and final output data.
        """
        hasher = hashlib.sha256()

        # Deterministically encode state transitions
        sorted_transitions = sorted(state_transitions, key=lambda x: (x.get("timestamp", ""), x.get("id", "")))
        transitions_str = json.dumps(sorted_transitions, sort_keys=True)
        hasher.update(f"transitions:{transitions_str}".encode("utf-8"))

        # Deterministically encode receipts (proof of execution)
        sorted_receipts = sorted(receipts, key=lambda x: (x.get("step_number", 0), x.get("signature", "")))
        receipts_str = json.dumps(sorted_receipts, sort_keys=True)
        hasher.update(f"receipts:{receipts_str}".encode("utf-8"))

        # Deterministically encode final output data
        output_str = json.dumps(output_data, sort_keys=True)
        hasher.update(f"output:{output_str}".encode("utf-8"))

        return hasher.hexdigest()
