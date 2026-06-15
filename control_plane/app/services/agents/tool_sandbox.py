"""
Owner: agent-platform
Status: beta
"""

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agent_tool_execution import AgentToolExecutionSandbox
from app.services.agents.sandbox_escape_analysis import SandboxEscapeAnalyzer
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def execute_in_sandbox(
    db: AsyncSession,
    tenant_id: str,
    invocation_id: Any,
    tool_name: str,
    tool_category: str,
    parameters: dict[str, Any],
    allowed_commands: list[str],
    timeout_seconds: int,
    output_limit_bytes: int = 50000,  # 50KB default limit
    tool_callable: Callable[..., Any] | None = None,
    sandbox_type: str = "mock",
) -> dict[str, Any]:
    """Executes a tool within a sandbox configuration.

    Checks command allowlists, enforces timeouts, handles output limit truncation,
    blocks unauthorized shell commands, and registers execution records.
    """
    settings = get_settings()

    # 1. Static Analysis & Escape Detection
    analyzer = SandboxEscapeAnalyzer()
    is_safe, reason = analyzer.analyze_parameters(tool_name, parameters)
    if not is_safe:
        logger.warning(f"Sandbox escape attempt blocked: {reason} for tool {tool_name}")
        raise ValueError(f"Security Policy Violation: {reason}")

    # Enforce shell command flag
    if tool_category == "shell_command":
        if not settings.agent_destructive_tools_enabled:
            raise ValueError("Shell commands are disabled by default.")

    # 2. Policy Check: Block simulation in production
    if not settings.agent_sandbox_allow_simulated_provider and sandbox_type in ["mock", "dry_run"]:
        logger.error(f"Simulated sandbox type '{sandbox_type}' is blocked in production.")
        raise ValueError(
            f"Security Policy Violation: Simulated execution mode '{sandbox_type}' is not allowed."
        )

    if settings.agent_code_sandbox_microvm_required and sandbox_type not in [
        "gvisor",
        "firecracker",
    ]:
        # If microvm is required, tool_sandbox must also use a secure provider if available,
        # or block if it's falling back to something weak.
        if sandbox_type == "mock":
            raise ValueError("MicroVM isolation is required; mock sandbox is insufficient.")

    # Resolve the command/operation name to check against allowlist
    command_to_run = (
        parameters.get("command")
        or parameters.get("cmd")
        or parameters.get("operation")
        or tool_name
    )
    if allowed_commands and "*" not in allowed_commands:
        if command_to_run not in allowed_commands:
            raise ValueError(
                f"Command '{command_to_run}' is not in the sandbox allowlist of commands: {allowed_commands}"
            )

    # Insert sandbox record in DB
    sandbox_record = AgentToolExecutionSandbox(
        invocation_id=invocation_id,
        tenant_id=tenant_id,
        sandbox_type=sandbox_type,
        status="running",
        allowed_commands=allowed_commands,
        runtime_limit_seconds=timeout_seconds,
        output_limit_bytes=output_limit_bytes,
        started_at=utc_now(),
    )
    db.add(sandbox_record)
    await db.flush()

    start_time = time.monotonic()
    output_truncated = False
    output_log = ""
    status = "success"
    output = {}

    try:
        if tool_callable is not None:
            # Enforce timeout and run
            if asyncio.iscoroutinefunction(tool_callable):
                output = await asyncio.wait_for(
                    tool_callable(**parameters), timeout=float(timeout_seconds)
                )
            else:

                def sync_wrapper():
                    return tool_callable(**parameters)

                output = await asyncio.wait_for(
                    asyncio.to_thread(sync_wrapper), timeout=float(timeout_seconds)
                )
        else:
            if sandbox_type == "mock":
                output = {
                    "status": "success",
                    "message": f"Sandbox execution mock output for command '{command_to_run}'.",
                    "execution_mode": "mock",
                    "simulated": True,
                }
            elif sandbox_type == "dry_run":
                output = {
                    "status": "dry_run_success",
                    "message": f"Sandbox dry-run completed for command '{command_to_run}'.",
                    "execution_mode": "dry_run",
                    "simulated": True,
                }
            else:
                raise ValueError(
                    f"Real sandbox execution for tool '{tool_name}' requires an explicit callable implementation. "
                    "Implicit mock fallback is blocked."
                )

        # Handle output serialization and truncation
        import json

        try:
            output_str = json.dumps(output)
        except Exception:
            output_str = str(output)

        output_log = output_str
        if len(output_str.encode("utf-8")) > output_limit_bytes:
            output_truncated = True
            output_log = output_str[:output_limit_bytes] + "\n...[TRUNCATED]"
            output = {
                "status": "truncated",
                "message": "Output exceeded size limit and was truncated.",
                "data": output_str[:output_limit_bytes],
            }

    except TimeoutError as te:
        status = "timeout"
        output_log = "Execution timed out."
        logger.error(f"Sandbox execution timed out after {timeout_seconds} seconds.")
        raise te
    except Exception as e:
        status = "failed"
        output_log = f"Execution failed: {str(e)}"
        logger.exception(f"Sandbox execution failed: {e}")
        raise e
    finally:
        latency = time.monotonic() - start_time
        sandbox_record.status = status
        sandbox_record.completed_at = utc_now()
        sandbox_record.output_truncated = output_truncated
        sandbox_record.output_log = output_log
        await db.flush()

    return output
