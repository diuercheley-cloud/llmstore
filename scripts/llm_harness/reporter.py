import json
import os
import time
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .defaults import REPORT_OUTPUT_PATH
from .models import ExecutionResult
from .sanitizer import Sanitizer


class Reporter:
    """
    Generates reports and summaries of agent executions.
    """

    def __init__(self, output_dir: str = REPORT_OUTPUT_PATH, git_tools=None):
        self.output_dir = output_dir
        self.git_tools = git_tools
        os.makedirs(output_dir, exist_ok=True)

        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def generate_summary(
        self,
        result: ExecutionResult,
        trace: list[dict[str, Any]],
        policy_info: dict[str, Any] | None = None,
    ):
        from .plugins import plugin_registry
        summary = {
            "success": result.success,
            "message": Sanitizer.sanitize_text(result.message),
            "error": Sanitizer.sanitize_text(result.error),
            "duration": result.duration,
            "total_duration_ms": result.total_duration_ms,
            "command_duration_ms": result.command_duration_ms,
            "agent_latency_ms": result.agent_latency_ms,
            "retry_count": result.retry_count,
            "total_tokens": getattr(result, "total_tokens", 0),
            "prompt_tokens": getattr(result, "prompt_tokens", 0),
            "completion_tokens": getattr(result, "completion_tokens", 0),
            "estimated_cost": getattr(result, "estimated_cost", 0.0),
            "cache_hits": getattr(result, "cache_hits", 0),
            "cache_misses": getattr(result, "cache_misses", 0),
            "timeout_adjusted": getattr(result, "timeout_adjusted", False),
            "time_to_first_action_ms": (result.metrics or {}).get("time_to_first_action_ms"),
            "time_to_final_ms": (result.metrics or {}).get("time_to_final_ms"),
            "final_tool_calling_mode": (result.metrics or {}).get("final_tool_calling_mode"),
            "selected_model": (result.metrics or {}).get("selected_model"),
            "supports_native_tool_calling": (result.metrics or {}).get(
                "supports_native_tool_calling"
            ),
            "native_tool_calling_probe": (result.metrics or {}).get("native_tool_calling_probe"),
            "fallback_reason": (result.metrics or {}).get("fallback_reason"),
            "fallback_strategy": (result.metrics or {}).get("fallback_strategy"),
            "lm_studio_compatibility": (result.metrics or {}).get("lm_studio_compatibility"),
            "post_final_llm_calls_blocked": (result.metrics or {}).get(
                "post_final_llm_calls_blocked", 0
            ),
            "llm_calls": result.llm_calls,
            "llm_provider": result.llm_provider,
            "llm_model": result.llm_model,
            "steps_count": len(trace),
            "trace_id": Sanitizer.sanitize_text(result.trace_id),
            "trace_hash": Sanitizer.sanitize_text(result.trace_hash),
            "trace": Sanitizer.sanitize_data(trace),
            "events": Sanitizer.sanitize_data(result.events),
            "blocked_actions": [
                Sanitizer.sanitize_text(event["message"])
                for event in result.events
                if event.get("event") == "policy.blocked"
            ],
            "policy": Sanitizer.sanitize_data(policy_info or {}),
            "provider": (policy_info.get("provider") if policy_info else "unknown"),
            "plugins": {
                name: {
                    "version": plugin.metadata.version,
                    "description": plugin.metadata.description,
                    "source": plugin.metadata.source,
                }
                for name, plugin in plugin_registry.plugins.items()
            }
        }

        if summary["provider"] == "stub":
            msg = "code agent provider is stub; no real task execution performed."
            summary["warning"] = msg

        if self.git_tools:
            summary["git_status"] = self.git_tools.run_git(["status", "--porcelain"])
            summary["git_diff"] = self.git_tools.run_git(["diff"])

        filename = f"report_{int(time.time())}.json"
        with open(os.path.join(self.output_dir, filename), "w") as f:
            json.dump(summary, f, indent=2)

        return filename

    def generate_markdown_report(
        self,
        result: ExecutionResult,
        blocked_actions: list[str] | None = None,
        provider: str = "openai-compatible",
    ):
        # Prepare data for template
        sanitized_result = result.model_copy()
        sanitized_result.message = Sanitizer.sanitize_text(result.message)
        sanitized_result.error = Sanitizer.sanitize_text(result.error)

        sanitized_blocked = [Sanitizer.sanitize_text(a) for a in (blocked_actions or [])]

        completed_events = []
        parsed_summaries = []
        raw_events = [
            e
            for e in result.events
            if e["event"] in ("action.completed", "action.failed", "policy.blocked")
        ]
        for e in raw_events:
            status_icon = (
                "✅"
                if e["status"] == "completed"
                else "❌"
                if e["status"] == "failed"
                else "🚫"
            )
            completed_events.append({
                "step": e["step"],
                "action_type": e["action_type"],
                "status_icon": status_icon,
                "status": e["status"],
                "duration_ms": e["duration_ms"],
                "message_short": Sanitizer.sanitize_text(e["message"])[:50],
            })
            parsed = e.get("metadata", {}).get("parsed")
            if isinstance(parsed, dict) and parsed.get("summary"):
                parsed_summaries.append(
                    {
                        "step": e["step"],
                        "action_type": e["action_type"],
                        "kind": parsed.get("kind", "generic"),
                        "summary": Sanitizer.sanitize_text(parsed.get("summary", "")),
                        "error_count": parsed.get("error_count", 0),
                        "warning_count": parsed.get("warning_count", 0),
                    }
                )

        slowest_actions = sorted(
            completed_events, key=lambda x: x["duration_ms"], reverse=True
        )[:3]

        template = self.jinja_env.get_template("report.md.jinja")
        git_status = ""
        git_diff = ""
        if self.git_tools:
            git_status = self.git_tools.run_git(["status", "--porcelain"])
            git_diff = self.git_tools.run_git(["diff"])

        return template.render(
            result=sanitized_result,
            completed_events=completed_events,
            slowest_actions=slowest_actions,
            parsed_summaries=parsed_summaries,
            blocked_actions=sanitized_blocked,
            trace_id=Sanitizer.sanitize_text(result.trace_id),
            trace_hash=Sanitizer.sanitize_text(result.trace_hash),
            provider=provider,
            git_status=git_status,
            git_diff=git_diff,
        )

    def generate_batch_markdown_report(self, results: list[dict[str, Any]]) -> str:
        total = len(results)
        success = sum(1 for r in results if r["success"])

        report = "# Batch Execution Summary\n\n"
        report += f"**Overall Status**: {success}/{total} successful\n\n"

        report += "| Scenario | Status | Message | Duration |\n"
        report += "| :--- | :--- | :--- | :--- |\n"

        for r in results:
            res_obj = r["result"]
            status = "✅ PASS" if r["success"] else "❌ FAIL"
            msg = Sanitizer.sanitize_text(res_obj.get("message") or res_obj.get("error") or "N/A")
            duration = f"{res_obj.get('duration', 0):.2f}s"
            report += f"| {r['name']} | {status} | {msg} | {duration} |\n"

        return report
