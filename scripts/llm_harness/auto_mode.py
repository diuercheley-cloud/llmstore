import json
import logging
from typing import Any

from .approval import ApprovalProvider
from .coding_loop import CodingLoop, ExecutionResult
from .diagnostics import diagnose_errors

logger = logging.getLogger(__name__)


class AutoModeApprovalProvider(ApprovalProvider):
    def __init__(
        self,
        require_approval_for_edits: bool = False,
        stop_on_risk: bool = False,
        max_auto_fixes: int = 3,
        mode: str = "auto",
        **kwargs,
    ):
        super().__init__(mode=mode, **kwargs)
        self.require_approval_for_edits = require_approval_for_edits
        self.stop_on_risk = stop_on_risk
        self.max_auto_fixes = max_auto_fixes
        self.edit_count = 0

    def request_approval(
        self,
        action: dict[str, Any],
        *,
        policy_decision: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        # If stop_on_risk is enabled and policy blocked or flagged it, we deny
        if self.stop_on_risk and policy_decision and not policy_decision.get("allowed", True):
            logger.warning("AutoMode: Risk detected and stop-on-risk is active. Denying action.")
            return False, action

        action_type = action.get("action_type") or action.get("type")
        is_edit = action_type in {
            "write_file",
            "apply_patch",
            "replace_content",
            "inline_edit",
            "edit",
        }

        if is_edit:
            self.edit_count += 1
            if self.edit_count > self.max_auto_fixes:
                logger.warning(
                    f"AutoMode: Max auto-fixes limit ({self.max_auto_fixes}) "
                    "reached. Denying action."
                )
                return False, action

        if is_edit and self.require_approval_for_edits:
            # Revert to interactive approval
            self.mode = "interactive"
            result = self._interactive_approval(action, policy_decision=policy_decision)
            self.mode = "auto"  # Reset to auto mode
            return result

        # Auto approve in auto mode
        return True, action


class AutoModeRunner:
    def __init__(
        self,
        coding_loop: CodingLoop,
        max_auto_fixes: int = 3,
        stop_on_risk: bool = False,
        require_approval_for_edits: bool = False,
    ):
        self.coding_loop = coding_loop
        self.max_auto_fixes = max_auto_fixes
        self.stop_on_risk = stop_on_risk
        self.require_approval_for_edits = require_approval_for_edits

        # Override the coding loop's approval provider
        self.coding_loop.approval_provider = AutoModeApprovalProvider(
            require_approval_for_edits=self.require_approval_for_edits,
            stop_on_risk=self.stop_on_risk,
            max_auto_fixes=self.max_auto_fixes,
            mode="auto",
        )
        # Ensure self_heal is enabled if auto mode is on
        self.coding_loop.self_heal = True

    async def run_task(self, task: str | list[dict[str, Any]]) -> ExecutionResult:
        logger.info(f"AutoMode starting for task: '{task}'")
        attempt = 0
        current_task = task
        max_attempts = max(1, self.max_auto_fixes + 1)
        last_result = ExecutionResult(success=False, error="Auto mode did not start")

        while attempt < max_attempts:
            attempt += 1
            result = await self.coding_loop.run(current_task)
            result.metrics["auto_mode_attempt"] = attempt
            result.metrics["auto_mode_max_attempts"] = max_attempts

            if result.success:
                result.metrics["auto_mode_retries_used"] = attempt - 1
                return result

            last_result = result
            failure_text = "\n".join(
                part for part in [result.message, result.error, result.output] if part
            )
            diagnostics = diagnose_errors(failure_text)
            policy_blocked = any(event.get("event") == "policy.blocked" for event in result.events)

            if diagnostics:
                logger.warning(f"AutoMode: Diagnostics of failure attempt {attempt}: {diagnostics}")
                result.metrics["auto_mode_diagnostics"] = [
                    diag.model_dump() for diag in diagnostics
                ]

            if self.stop_on_risk and policy_blocked:
                result.error = (
                    f"{result.error or 'Failed'}. "
                    "Auto mode stopped because policy risk was detected."
                )
                result.metrics["auto_mode_stopped_on_risk"] = True
                return result

            if attempt >= max_attempts:
                break

            current_task = self._build_retry_task(
                original_task=task,
                previous_result=result,
                diagnostics=diagnostics,
                attempt=attempt + 1,
            )

        final_failure_text = "\n".join(
            part for part in [last_result.message, last_result.error, last_result.output] if part
        )
        diagnostics = diagnose_errors(final_failure_text)
        if diagnostics:
            last_result.error = (
                f"{last_result.error or 'Failed'}. Diagnostics: "
                f"{json.dumps([d.model_dump() for d in diagnostics])}"
            )
            last_result.metrics["auto_mode_diagnostics"] = [
                diag.model_dump() for diag in diagnostics
            ]

        last_result.metrics["auto_mode_retries_used"] = max(0, attempt - 1)
        return last_result

    def _build_retry_task(
        self,
        original_task: str | list[dict[str, Any]],
        previous_result: ExecutionResult,
        diagnostics: list[Any],
        attempt: int,
    ) -> str | list[dict[str, Any]]:
        diagnostics_lines = []
        for diag in diagnostics[:5]:
            diagnostics_lines.append(
                f"- file={diag.file} line={diag.line} severity={diag.severity}: {diag.message}"
            )

        retry_text = (
            f"Auto Mode retry attempt {attempt}.\n"
            "Continue from the current workspace state. Review the previous failure, "
            "apply the smallest safe fix, rerun verification, and only finish once the "
            "task is complete.\n\n"
            f"Previous message: {previous_result.message or ''}\n"
            f"Previous error: {previous_result.error or ''}\n"
        )
        if diagnostics_lines:
            retry_text += "Diagnostics:\n" + "\n".join(diagnostics_lines) + "\n"

        if isinstance(original_task, list):
            retried = []
            injected = False
            for block in original_task:
                if block.get("type") == "text" and not injected:
                    retried.append(
                        {
                            **block,
                            "text": f"{block.get('text', '')}\n\n{retry_text}",
                        }
                    )
                    injected = True
                else:
                    retried.append(block)
            if not injected:
                retried.insert(0, {"type": "text", "text": retry_text})
            return retried

        return f"{original_task}\n\n{retry_text}"
