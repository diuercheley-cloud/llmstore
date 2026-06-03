import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

class ApprovalProvider:
    def __init__(self, mode: str = "auto", default_policy: str = "deny"):
        self.mode = mode
        self.default_policy = default_policy

    def request_approval(self, action: dict[str, Any]) -> bool:
        if self.mode == "auto":
            return True
        if self.mode == "deny":
            return False

        if self.mode == "interactive":
            return self._interactive_approval(action)

        if self.mode == "non_interactive":
            return self.default_policy == "allow"

        return False

    def _interactive_approval(self, action: dict[str, Any]) -> bool:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "Approval mode 'interactive' requires a TTY (stdin must be a terminal). "
                "Use --approval-mode auto to auto-approve or --approval-mode deny to reject all."
            )

        print("\n" + "="*50)
        print("ACTION APPROVAL REQUIRED")
        print("="*50)
        print(f"Action Type: {action.get('action_type')}")
        print(f"Reason: {action.get('reason')}")
        print("-" * 20)

        # Show relevant payload info
        if action.get("action_type") == "apply_patch":
            print(f"Diff length: {len(action.get('diff', ''))} chars")
        elif action.get("action_type") == "run_shell":
            print(f"Command: {action.get('command')}")
        elif action.get("action_type") == "read_file":
            print(f"Path: {action.get('path')}")
        else:
            print(f"Payload: {action}")

        while True:
            choice = input("\nApprove? [y]es / [n]o / [a]bort: ").lower().strip()
            if choice == 'y':
                return True
            if choice == 'n':
                return False
            if choice == 'a':
                raise InterruptedError("User aborted execution")
            print("Invalid choice. Please enter y, n, or a.")
