# Owner: agent-platform
import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from app.core.config import get_settings
from app.models.agents import AgentRegistryEntry, AgentTool, AgentToolInvocation
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents.tool_audit import log_audit_event, sanitize_payload
from app.services.agents.tool_credentials import resolve_credential
from app.services.agents.tool_policy import evaluate_tool_policy
from app.services.agents.tool_quota import check_and_increment_quota
from app.services.agents.tool_rollback import (
    register_rollback_action,
    register_side_effect,
    rollback_invocation_side_effects,
)

# Import security modules
from app.services.agents.tool_sandbox import execute_in_sandbox
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

def hash_payload(data: Any) -> str:
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
    agent_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[str] = None,
    is_dry_run: bool = False,
    tool_callable: Optional[Callable[..., Any]] = None,
    rollback_callable: Optional[Callable[..., Any]] = None,
    executed_by: str = "agent"
) -> Dict[str, Any]:
    settings = get_settings()
    effective_tenant = tenant_id or "default"
    effective_agent_id = agent_id or (agent.agent_id if agent else None)
    input_hash = hash_payload(parameters)

    if not is_dry_run and not settings.agent_tool_execution_enabled:
        raise ValueError("Tool execution is disabled by feature flag.")
    if tool.side_effect_level == "destructive" and not settings.agent_destructive_tools_enabled:
        raise ValueError("Destructive tool execution is disabled by feature flag.")

    # 0. Check Execution Limits (Calls)
    if run_id:
        stmt_count = select(func.count(AgentToolInvocation.id)).where(
            AgentToolInvocation.run_id == run_id,
            AgentToolInvocation.agent_tool_id == tool.id
        )
        res_count = await db.execute(stmt_count)
        call_count = res_count.scalar() or 0
        if call_count >= tool.max_calls_per_run:
             raise ValueError(f"Tool {tool.name} exceeded max_calls_per_run ({tool.max_calls_per_run}) for run {run_id}.")

    # 1. Prepare invocation record
    invocation = AgentToolInvocation(
        agent_tool_id=tool.id,
        run_id=run_id,
        agent_id=effective_agent_id,
        input_hash=input_hash,
        executed_by=executed_by,
        is_dry_run=is_dry_run,
        is_rollback=False,
        status="success"
    )
    db.add(invocation)
    await db.flush()

    await log_audit_event(
        db=db, tenant_id=effective_tenant, event_type="tool_invocation_started",
        invocation_id=invocation.id, agent_id=effective_agent_id,
        agent_tool_id=tool.id, details={"parameters": parameters, "is_dry_run": is_dry_run}
    )

    resolved_secret = await resolve_credential(
        db=db, tenant_id=effective_tenant, agent_tool_id=tool.id, agent_id=effective_agent_id
    )
    modified_parameters = dict(parameters)
    modified_parameters["db"] = db
    if resolved_secret:
        modified_parameters["api_key"] = resolved_secret
    if "tenant_id" not in modified_parameters and effective_tenant:
        modified_parameters["tenant_id"] = effective_tenant
    if "agent_id" not in modified_parameters and effective_agent_id:
        modified_parameters["agent_id"] = effective_agent_id
    if "run_id" not in modified_parameters and run_id:
        modified_parameters["run_id"] = run_id

    await check_and_increment_quota(
        db=db,
        tenant_id=effective_tenant,
        agent_id=effective_agent_id,
        tool_id=tool.id,
        side_effect_level=tool.side_effect_level,
    )

    start_time = time.monotonic()
    output = {}
    side_effect = None
    rollback_action = None
    eff_rollback_callable = rollback_callable

    retry_policy = tool.retry_policy or {}
    max_retries = retry_policy.get("max_attempts", 1) - 1
    backoff = retry_policy.get("initial_backoff", 1)
    
    can_retry = tool.side_effect_level in ("none", "read")
    if not can_retry: max_retries = 0

    attempt = 0
    while True:
        try:
            policy_decision = await evaluate_tool_policy(
                db=db, tool=tool, agent=agent, agent_id=effective_agent_id, tenant_id=effective_tenant, is_dry_run=is_dry_run, run_id=run_id
            )

            if not policy_decision.allowed:
                raise ValueError(f"Policy evaluation denied access: {policy_decision.reason}")
            
            if policy_decision.requires_approval:
                has_approval = False
                if executed_by in ("human", "admin"):
                    has_approval = True
                elif run_id:
                    from app.models.agents import AgentApprovalRequest
                    stmt_approval = select(AgentApprovalRequest).where(
                        AgentApprovalRequest.agent_run_id == run_id,
                        AgentApprovalRequest.status == "approved"
                    )
                    res_approval = await db.execute(stmt_approval)
                    approvals = res_approval.scalars().all()
                    for app_req in approvals:
                        if (app_req.sanitized_context or {}).get("tool_name") == tool.name:
                            has_approval = True
                            break
                if not has_approval:
                    raise ValueError("Tool execution requires human approval.")

            # Try to resolve tool_callable from adapter_registry
            eff_tool_callable = tool_callable
            eff_rollback_callable = rollback_callable
            is_dry_callable = False

            if eff_tool_callable is None and settings.agent_tool_adapters_enabled:
                adapter = adapter_registry.get_adapter(tool.name)
                if adapter:
                    eff_tool_callable = adapter.execute
                    if is_dry_run:
                        eff_tool_callable = adapter.dry_run
                        is_dry_callable = True
                    if tool.rollback_supported:
                        eff_rollback_callable = adapter.rollback

            if is_dry_run:
                if eff_tool_callable and is_dry_callable:
                    if asyncio.iscoroutinefunction(eff_tool_callable):
                        output = await asyncio.wait_for(eff_tool_callable(**modified_parameters), timeout=float(tool.timeout_seconds))
                    else:
                        output = eff_tool_callable(**modified_parameters)
                else:
                    output = {
                        "status": "dry_run_success",
                        "message": "Dry-run simulation completed successfully.",
                        "execution_mode": "dry_run",
                        "simulated": True,
                    }
                invocation.status = "dry_run"
                break
            else:
                if tool.side_effect_level in ("write", "destructive", "external"):
                    resource_id = parameters.get("resource_id")
                    if resource_id is None:
                        resource_id = parameters.get("id")
                    side_effect = await register_side_effect(
                        db=db,
                        tenant_id=effective_tenant,
                        invocation_id=invocation.id,
                        side_effect_level=tool.side_effect_level,
                        description=f"Tool {tool.name} invoked with side effects",
                        resource_id=resource_id,
                        change_payload=sanitize_payload(parameters),
                    )
                    if tool.rollback_supported:
                        compensation_payload = {}
                        if resource_id is not None:
                            compensation_payload["resource_id"] = resource_id
                        rollback_action = await register_rollback_action(
                            db=db,
                            tenant_id=effective_tenant,
                            side_effect_id=side_effect.id,
                            compensation_action=f"rollback:{tool.name}",
                            compensation_payload=compensation_payload,
                        )

                if settings.agent_tool_sandbox_enabled:
                    output = await execute_in_sandbox(
                        db=db, tenant_id=effective_tenant, invocation_id=invocation.id,
                        tool_name=tool.name, tool_category=tool.category,
                        parameters=modified_parameters, allowed_commands=["*"],
                        timeout_seconds=int(tool.timeout_seconds),
                        tool_callable=eff_tool_callable,
                        sandbox_type="real",
                    )
                else:
                    if eff_tool_callable is not None:
                        if asyncio.iscoroutinefunction(eff_tool_callable):
                            output = await asyncio.wait_for(eff_tool_callable(**modified_parameters), timeout=float(tool.timeout_seconds))
                        else:
                            output = await asyncio.wait_for(asyncio.to_thread(lambda: eff_tool_callable(**modified_parameters)), timeout=float(tool.timeout_seconds))
                    else:
                        raise ValueError(
                            f"Real execution requested for tool '{tool.name}', but no concrete implementation is registered."
                        )
                break

        except Exception as e:
            if side_effect is not None and tool.rollback_supported:
                rolled_back = await rollback_invocation_side_effects(
                    db=db,
                    tenant_id=effective_tenant,
                    invocation_id=invocation.id,
                    rollback_callable=rollback_callable or eff_rollback_callable,
                )
                if rolled_back:
                    invocation.status = "rolled_back"
            if attempt < max_retries:
                attempt += 1
                logger.warning(f"Retrying tool {tool.name} (attempt {attempt}/{max_retries}) due to: {e}")
                await asyncio.sleep(backoff * (2 ** (attempt - 1)))
                continue
            
            latency_ms = int((time.monotonic() - start_time) * 1000)
            invocation.latency_ms = latency_ms
            if invocation.status != "rolled_back":
                invocation.status = "failed"
            invocation.error_message = str(e)
            
            await log_audit_event(
                db=db, tenant_id=effective_tenant, event_type="tool_invocation_failed",
                invocation_id=invocation.id, agent_id=effective_agent_id,
                agent_tool_id=tool.id, decision="failed", reason=str(e)
            )
            await db.commit()
            raise e

    latency_ms = int((time.monotonic() - start_time) * 1000)
    invocation.latency_ms = latency_ms
    invocation.output_hash = hash_payload(output)
    
    await log_audit_event(
        db=db, tenant_id=effective_tenant, event_type="tool_invocation_completed",
        invocation_id=invocation.id, agent_id=effective_agent_id,
        agent_tool_id=tool.id, decision="success", details={"output": output}
    )
    await db.commit()
    return output
