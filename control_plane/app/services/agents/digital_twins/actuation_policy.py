import logging
from typing import Dict, Any, Optional, List, Set

logger = logging.getLogger(__name__)


class ActuationPolicy:
    """
    Enforces actuation policies for digital twins.
    Validates commands against safety rules, interlocks, and boundaries.

    Policy levels:
      - allow_all: No restrictions (dev mode, default)
      - safe: Allow safe commands only (no destructive operations)
      - restricted: Allow only read/observe commands
      - deny_all: Block all actuation
    """

    SAFE_COMMANDS: Set[str] = {
        "read", "observe", "status", "ping", "identify",
        "get_temperature", "get_pressure", "get_position",
    }

    DESTRUCTIVE_COMMANDS: Set[str] = {
        "shutdown", "reset", "calibrate", "override",
        "disable_safety", "emergency_stop_reset",
        "firmware_update", "reboot",
    }

    REQUIRES_APPROVAL: Set[str] = {
        "shutdown", "calibrate", "override", "disable_safety",
        "firmware_update", "reset",
    }

    def __init__(self, policy_level: str = "safe"):
        self.policy_level = policy_level

    def validate(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        twin_type: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate a command against the current policy level.
        Returns a dict with keys: allowed, reason, requires_approval, severity.
        """
        command_lower = command.strip().lower()
        params = params or {}

        if self.policy_level == "allow_all":
            return {"allowed": True, "reason": "Policy level: allow_all", "requires_approval": False, "severity": "info"}

        if self.policy_level == "deny_all":
            return {"allowed": False, "reason": "Policy level: deny_all", "requires_approval": False, "severity": "critical"}

        if self.policy_level == "restricted":
            if command_lower in self.SAFE_COMMANDS:
                return {"allowed": True, "reason": "Safe read command", "requires_approval": False, "severity": "info"}
            return {"allowed": False, "reason": f"Policy level restricted: '{command}' not in safe command set", "requires_approval": False, "severity": "warning"}

        if self.policy_level == "safe":
            if command_lower in self.DESTRUCTIVE_COMMANDS:
                return {"allowed": False, "reason": f"Destructive command '{command}' blocked by safe policy", "requires_approval": True, "severity": "high"}
            if command_lower in self.REQUIRES_APPROVAL:
                return {"allowed": True, "reason": f"Command '{command}' requires approval", "requires_approval": True, "severity": "medium"}

            if risk_level == "critical":
                return {"allowed": True, "reason": "Command allowed pending risk review", "requires_approval": True, "severity": "critical"}

            return {"allowed": True, "reason": "Command allowed by safe policy", "requires_approval": False, "severity": "info"}

        return {"allowed": True, "reason": f"Unknown policy level '{self.policy_level}', defaulting to allow", "requires_approval": False, "severity": "info"}

    def validate_batch(
        self,
        commands: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results = []
        for cmd in commands:
            result = self.validate(
                command=cmd.get("command", ""),
                params=cmd.get("params"),
                twin_type=cmd.get("twin_type"),
                risk_level=cmd.get("risk_level"),
            )
            results.append({**cmd, "policy_result": result})
        return results

    def requires_approval(self, command: str) -> bool:
        return command.strip().lower() in self.REQUIRES_APPROVAL

    def is_destructive(self, command: str) -> bool:
        return command.strip().lower() in self.DESTRUCTIVE_COMMANDS
