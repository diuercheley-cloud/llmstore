"""
Owner: agent-platform
Status: beta
"""
import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agent_tool_execution import AgentToolExecutionSandbox

logger = logging.getLogger(__name__)


async def execute_in_sandbox(
    db: AsyncSession,
    tenant_id: str,
    invocation_id: Any,
    tool_name: str,
    tool_category: str,
    parameters: Dict[str, Any],
    allowed_commands: List[str],
    timeout_seconds: int,
    output_limit_bytes: int = 50000,  # 50KB default limit
    tool_callable: Optional[Callable[..., Any]] = None,
    sandbox_type: str = "mock",
) -> Dict[str, Any]:
    """Executes a tool within a sandbox configuration.
    
    Checks command allowlists, enforces timeouts, handles output limit truncation,
    blocks unauthorized shell commands, and registers execution records.
    """
    settings = get_settings()

    # Enforce shell command flag
    if tool_category == "shell_command":
        if not settings.agent_destructive_tools_enabled:
            raise ValueError("Shell commands are disabled by default.")

    # Resolve the command/operation name to check against allowlist
    command_to_run = parameters.get("command") or parameters.get("cmd") or parameters.get("operation") or tool_name
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
                    tool_callable(**parameters),
                    timeout=float(timeout_seconds)
                )
            else:
                def sync_wrapper():
                    return tool_callable(**parameters)
                output = await asyncio.wait_for(
                    asyncio.to_thread(sync_wrapper),
                    timeout=float(timeout_seconds)
                )
        else:
            # Default mock simulation
            output = {
                "status": "success",
                "message": f"Sandbox execution mock output for command '{command_to_run}'."
            }

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
                "data": output_str[:output_limit_bytes]
            }

    except asyncio.TimeoutError as te:
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
