import contextlib
import difflib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from typing import Any

from .sanitizer import Sanitizer


class ApprovalProvider:
    def __init__(
        self,
        mode: str = "auto",
        default_policy: str | None = "deny",
        edit_action_before_run: bool = False,
    ):
        self.mode = mode
        self.default_policy = default_policy
        self.edit_action_before_run = edit_action_before_run
        self._always_allow = False

    def request_approval(
        self,
        action: dict[str, Any],
        *,
        policy_decision: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        if self.mode == "auto" or self._always_allow:
            return True, action
        if self.mode == "deny":
            return False, action
        if self.mode == "non_interactive":
            return self.default_policy == "allow", action
        if self.mode == "interactive":
            return self._interactive_approval(action, policy_decision=policy_decision)
        return False, action

    def _interactive_approval(
        self,
        action: dict[str, Any],
        *,
        policy_decision: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        if not sys.stdin.isatty():
            if self.default_policy in {"allow", "deny"}:
                return self.default_policy == "allow", action
            raise RuntimeError(
                "Approval mode 'interactive' requires a TTY. "
                "Set --approval-default allow|deny for non-TTY runs."
            )

        current_action = dict(action)
        while True:
            self._print_action_summary(current_action, policy_decision)
            prompt = "Approve? [y]es / [n]o / [e]dit / [a]bort / approve al[w]ays: "
            choice = input(prompt).lower().strip()
            if choice in {"y", "yes"}:
                return True, current_action
            if choice in {"d", "n", "no"}:
                return False, current_action
            if choice in {"a", "b", "abort"}:
                raise InterruptedError("User aborted execution")
            if choice == "w":
                self._always_allow = True
                return True, current_action
            if choice == "e":
                if not self.edit_action_before_run:
                    print("Editing is disabled. Use --edit-action-before-run to enable it.")
                    continue
                current_action = self._edit_action(current_action)
                continue
            print("Invalid choice. Please enter a, d, e, b, or w.")

    def _print_action_summary(
        self,
        action: dict[str, Any],
        policy_decision: dict[str, Any] | None,
    ) -> None:
        print("\n" + "=" * 60)
        print("ACTION APPROVAL REQUIRED")
        print("=" * 60)
        print(f"Action Type: {action.get('action_type')}")
        print(f"Reason: {Sanitizer.sanitize_text(action.get('reason') or '')}")
        if policy_decision:
            risk = policy_decision.get("policy_level") or "policy"
            decision = "allow" if policy_decision.get("allowed", True) else "deny"
            reason = Sanitizer.sanitize_text(policy_decision.get("reason") or "")
            print(f"Policy: {decision} ({risk}) {reason}".rstrip())
        print("-" * 24)
        summary = self._summarize_payload(action)
        if summary:
            print(summary)

    def _summarize_payload(self, action: dict[str, Any]) -> str:
        action_type = action.get("action_type")
        if action_type == "apply_patch":
            return self._preview_text(action.get("diff", ""), label="Diff Preview")
        if action_type == "write_file":
            path = action.get("path", "")
            preview = self._preview_text(
                action.get("content", ""),
                label="Content Preview",
            )
            return f"Path: {path}\n{preview}"
        if action_type == "replace_content":
            path = action.get("path", "")
            before = str(action.get("old_content", ""))
            after = str(action.get("new_content", ""))
            diff = "\n".join(
                difflib.unified_diff(
                    before.splitlines(),
                    after.splitlines(),
                    fromfile=f"{path} (old)",
                    tofile=f"{path} (new)",
                    lineterm="",
                )
            )
            return f"Path: {path}\n" + self._preview_text(diff, label="Diff Preview")
        if action_type == "run_shell":
            return f"Command: {Sanitizer.sanitize_text(action.get('command') or '')}"
        if action_type in {"read_file", "list_files"}:
            return f"Path: {action.get('path', '.')}"
        payload = {k: v for k, v in action.items() if k not in {"reason"}}
        sanitized = Sanitizer.sanitize_data(payload)
        return f"Payload: {json.dumps(sanitized, ensure_ascii=True)[:500]}"

    def _preview_text(self, content: str, *, label: str) -> str:
        sanitized = Sanitizer.sanitize_text(content)
        preview = sanitized[:1200]
        if len(sanitized) > len(preview):
            preview += "\n... (truncated)"
        return f"{label}:\n{preview}"

    def _edit_action(self, action: dict[str, Any]) -> dict[str, Any]:
        serialized = json.dumps(Sanitizer.sanitize_data(action), indent=2, ensure_ascii=True)
        editor = os.getenv("VISUAL") or os.getenv("EDITOR") or "vi"
        with tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=".json",
            prefix="llm-harness-action-",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            temp_path = handle.name
        try:
            subprocess.run(
                shlex.split(editor) + [temp_path],
                check=True,
            )
            with open(temp_path, encoding="utf-8") as handle:
                edited = handle.read().strip()
        finally:
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
        if not edited:
            return action
        parsed = json.loads(edited)
        if not isinstance(parsed, dict):
            raise ValueError("Edited action must be a JSON object")
        return parsed
