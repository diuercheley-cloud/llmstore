import uuid
import time
import asyncio
import hashlib
import json
import logging
from typing import Any, Callable, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentTool, AgentToolInvocation, AgentRegistryEntry
from app.core.config import get_settings
from app.services.agents.tool_policy import evaluate_tool_policy
from app.core.time import utc_now

logger = logging.getLogger(__name__)


def hash_payload(data: Any) -> str:
    """Computes a canonical SHA-256 hash of a python dictionary/JSON serializable structure."""
    try:
        serialized = json.dumps(data, sort_keys=True)
    except Exception:
        serialized = str(data)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def execute_tool(
    db: AsyncSession,
    tool: AgentTool,
    parameters: Dict[str, Any],
    run_id: Optional[uuid.UUID] = None,
    agent: Optional[AgentRegistryEntry] = None,
    tenant_id: Optional[str] = None,
    is_dry_run: bool = False,
    tool_callable: Optional[Callable[..., Any]] = None,
    rollback_callable: Optional[Callable[..., Any]] = None,
    executed_by: str = "agent"
) -> Dict[str, Any]:
    """Coordinates tool execution under safety policies, feature flags, timeout, and rollback rules.
    
    Logs all execution metadata in AgentToolInvocation using SHA-256 parameter hashes.
    """
    settings = get_settings()
    # 8. Policy check antes da execução.
    policy_decision = await evaluate_tool_policy(
        db=db,
        tool=tool,
        agent=agent,
        tenant_id=tenant_id,
        is_dry_run=is_dry_run
    )
    if not policy_decision.allowed:
        raise ValueError(f"Policy evaluation denied access: {policy_decision.reason}")
    if policy_decision.requires_approval:
        raise ValueError("Tool execution requires human approval.")

    # Enforce destructive tools gate
    is_destructive = (
        tool.side_effect_level == "destructive" or
        tool.category in ("admin_operation", "shell_command")
    )
    if is_destructive and not settings.agent_destructive_tools_enabled:
        raise ValueError("Destructive tool execution is disabled by feature flag.")

    # Calculate input hash
    input_hash = hash_payload(parameters)

    # Prepare invocation record
    invocation = AgentToolInvocation(
        agent_tool_id=tool.id,
        run_id=run_id,
        agent_id=agent.agent_id if agent else None,
        input_hash=input_hash,
        executed_by=executed_by,
        is_dry_run=is_dry_run,
        is_rollback=False,
        status="success"
    )

    start_time = time.monotonic()
    output = {}
    
    try:
        if is_dry_run:
            # dry-run não causa side effect
            output = {"status": "dry_run_success", "message": "Dry-run simulation completed successfully."}
            invocation.status = "dry_run"
        else:
            # Nenhuma tool real executa se AGENT_TOOL_EXECUTION_ENABLED=false
            if not settings.agent_tool_execution_enabled:
                raise ValueError("Tool execution is disabled by feature flag (AGENT_TOOL_EXECUTION_ENABLED=false).")

            if tool_callable is not None:
                # Enforce programmatic timeout
                if asyncio.iscoroutinefunction(tool_callable):
                    output = await asyncio.wait_for(
                        tool_callable(**parameters),
                        timeout=float(tool.timeout_seconds)
                    )
                else:
                    def sync_wrapper():
                        return tool_callable(**parameters)
                    output = await asyncio.wait_for(
                        asyncio.to_thread(sync_wrapper),
                        timeout=float(tool.timeout_seconds)
                    )
            else:
                # If no callable provided, return dummy success
                output = {"status": "success", "message": f"Simulated execution of tool {tool.name}"}

        invocation.output_hash = hash_payload(output)
        
    except (asyncio.TimeoutError, Exception) as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        invocation.latency_ms = latency_ms
        invocation.status = "failed"
        invocation.error_message = str(e) or type(e).__name__
        
        # Rollback / Compensation if supported
        if tool.rollback_supported:
            try:
                if rollback_callable:
                    if asyncio.iscoroutinefunction(rollback_callable):
                        await rollback_callable()
                    else:
                        await asyncio.to_thread(rollback_callable)
                invocation.status = "rolled_back"
            except Exception as rollback_err:
                logger.error(f"Rollback failed for tool {tool.name}: {rollback_err}")
                invocation.error_message += f" | Rollback failed: {rollback_err}"
        
        db.add(invocation)
        await db.commit()
        raise e

    latency_ms = int((time.monotonic() - start_time) * 1000)
    invocation.latency_ms = latency_ms
    db.add(invocation)
    await db.commit()
    
    return output
