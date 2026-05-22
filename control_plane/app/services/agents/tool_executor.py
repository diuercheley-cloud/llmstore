import uuid
import time
import asyncio
import hashlib
import json
import logging
from typing import Any, Callable, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentTool, AgentToolInvocation, AgentRegistryEntry
from app.core.config import get_settings
from app.services.agents.tool_policy import evaluate_tool_policy
from app.core.time import utc_now

# Import new security modules
from app.services.agents.tool_sandbox import execute_in_sandbox
from app.services.agents.tool_credentials import resolve_credential
from app.services.agents.tool_quota import check_and_increment_quota, QuotaExceededError
from app.services.agents.tool_rollback import (
    register_side_effect,
    register_rollback_action,
    rollback_invocation_side_effects,
)
from app.services.agents.tool_audit import log_audit_event
from app.services.agents.tool_adapter_registry import adapter_registry

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
    Integrates secure sandbox, delegated credentials, daily quotas, side effects, rollback plans, and audit trailing.
    """
    settings = get_settings()
    effective_tenant = tenant_id or "default"

    # Calculate input hash
    input_hash = hash_payload(parameters)

    # 1. Prepare invocation record
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
    db.add(invocation)
    await db.flush() # Flush to get invocation.id

    # Log initial invocation start
    await log_audit_event(
        db=db,
        tenant_id=effective_tenant,
        event_type="tool_invocation_started",
        invocation_id=invocation.id,
        agent_id=agent.agent_id if agent else None,
        agent_tool_id=tool.id,
        details={"parameters": parameters, "is_dry_run": is_dry_run}
    )

    # 2. Policy check antes da execução.
    policy_decision = await evaluate_tool_policy(
        db=db,
        tool=tool,
        agent=agent,
        tenant_id=effective_tenant,
        is_dry_run=is_dry_run
    )

    await log_audit_event(
        db=db,
        tenant_id=effective_tenant,
        event_type="policy_evaluated",
        invocation_id=invocation.id,
        agent_id=agent.agent_id if agent else None,
        agent_tool_id=tool.id,
        decision="allow" if policy_decision.allowed else "deny",
        reason=policy_decision.reason,
        details=policy_decision.to_dict()
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
                ctx = app_req.sanitized_context or {}
                if ctx.get("tool_name") == tool.name:
                    has_approval = True
                    break
        if not has_approval:
            raise ValueError("Tool execution requires human approval.")

    # 3. Enforce destructive tools gate
    if tool.category == "shell_command" and not settings.agent_destructive_tools_enabled:
        await log_audit_event(
            db=db,
            tenant_id=effective_tenant,
            event_type="gate_check_failed",
            invocation_id=invocation.id,
            agent_id=agent.agent_id if agent else None,
            agent_tool_id=tool.id,
            decision="deny",
            reason="Shell commands are disabled by default."
        )
        raise ValueError("Shell commands are disabled by default.")

    is_destructive = (
        tool.side_effect_level == "destructive" or
        tool.category == "admin_operation"
    )
    if is_destructive and not settings.agent_destructive_tools_enabled:
        await log_audit_event(
            db=db,
            tenant_id=effective_tenant,
            event_type="gate_check_failed",
            invocation_id=invocation.id,
            agent_id=agent.agent_id if agent else None,
            agent_tool_id=tool.id,
            decision="deny",
            reason="Destructive tool execution is disabled by feature flag."
        )
        raise ValueError("Destructive tool execution is disabled by feature flag.")

    # 4. Quota enforcement
    if not is_dry_run:
        try:
            await check_and_increment_quota(
                db=db,
                tenant_id=effective_tenant,
                agent_id=agent.agent_id if agent else None,
                tool_id=tool.id,
                side_effect_level=tool.side_effect_level
            )
        except QuotaExceededError as qe:
            await log_audit_event(
                db=db,
                tenant_id=effective_tenant,
                event_type="quota_check_failed",
                invocation_id=invocation.id,
                agent_id=agent.agent_id if agent else None,
                agent_tool_id=tool.id,
                decision="deny",
                reason=str(qe)
            )
            raise qe

    # 5. Resolve delegated credentials
    resolved_secret = await resolve_credential(
        db=db,
        tenant_id=effective_tenant,
        agent_tool_id=tool.id,
        agent_id=agent.agent_id if agent else None
    )
    
    modified_parameters = dict(parameters)
    if resolved_secret:
        await log_audit_event(
            db=db,
            tenant_id=effective_tenant,
            event_type="credential_grant_resolved",
            invocation_id=invocation.id,
            agent_id=agent.agent_id if agent else None,
            agent_tool_id=tool.id,
            decision="allow",
            reason="Active delegated credential resolved for tool execution."
        )
        # Inject the secret into parameter keys matching credential pattern
        if tool.input_schema_json and "properties" in tool.input_schema_json:
            props = tool.input_schema_json["properties"]
            inserted = False
            for k in props:
                if any(p in k.lower() for p in ["api_key", "secret", "password", "token", "auth", "credential"]):
                    modified_parameters[k] = resolved_secret
                    inserted = True
            if not inserted:
                modified_parameters["api_key"] = resolved_secret
        else:
            modified_parameters["api_key"] = resolved_secret

    start_time = time.monotonic()
    output = {}

     # Try to resolve tool_callable from adapter_registry if not provided
    effective_tool_callable = tool_callable
    effective_rollback_callable = rollback_callable
    is_dry_run_callable = False

    if effective_tool_callable is None and settings.agent_tool_adapters_enabled:
        adapter = adapter_registry.get_adapter(tool.name)
        if adapter:
            effective_tool_callable = adapter.execute
            if is_dry_run:
                effective_tool_callable = adapter.dry_run
                is_dry_run_callable = True
            
            if tool.rollback_supported:
                effective_rollback_callable = adapter.rollback

    try:
        if is_dry_run:
            # dry-run não causa side effect
            if effective_tool_callable and is_dry_run_callable:
                 if asyncio.iscoroutinefunction(effective_tool_callable):
                        output = await asyncio.wait_for(
                            effective_tool_callable(**modified_parameters),
                            timeout=float(tool.timeout_seconds)
                        )
                 else:
                        output = effective_tool_callable(**modified_parameters)
            else:
                output = {"status": "dry_run_success", "message": "Dry-run simulation completed successfully."}
            
            invocation.status = "dry_run"
            
            # Execute mock sandbox to record sandbox audit logs as dry run
            if settings.agent_tool_sandbox_enabled:
                await execute_in_sandbox(
                    db=db,
                    tenant_id=effective_tenant,
                    invocation_id=invocation.id,
                    tool_name=tool.name,
                    tool_category=tool.category,
                    parameters=modified_parameters,
                    allowed_commands=["*"],
                    timeout_seconds=int(tool.timeout_seconds),
                    tool_callable=None
                )
        else:
            # Nenhuma tool real executa se AGENT_TOOL_EXECUTION_ENABLED=false
            if not settings.agent_tool_execution_enabled:
                raise ValueError("Tool execution is disabled by feature flag (AGENT_TOOL_EXECUTION_ENABLED=false).")

            # Register side effect and rollback plan for write/destructive tools BEFORE execution
            if tool.side_effect_level in ("write", "destructive"):
                side_effect = await register_side_effect(
                    db=db,
                    tenant_id=effective_tenant,
                    invocation_id=invocation.id,
                    side_effect_level=tool.side_effect_level,
                    description=f"Generated mutation via {tool.name} tool.",
                    resource_id=parameters.get("resource_id") or parameters.get("id"),
                    change_payload=parameters
                )
                await log_audit_event(
                    db=db,
                    tenant_id=effective_tenant,
                    event_type="side_effect_registered",
                    invocation_id=invocation.id,
                    agent_id=agent.agent_id if agent else None,
                    agent_tool_id=tool.id,
                    details={"side_effect_id": side_effect.id, "level": tool.side_effect_level}
                )

                if tool.rollback_supported:
                    rollback_action = await register_rollback_action(
                        db=db,
                        tenant_id=effective_tenant,
                        side_effect_id=side_effect.id,
                        compensation_action=f"rollback_{tool.name}",
                        compensation_payload={"resource_id": parameters.get("resource_id") or parameters.get("id") or ""}
                    )
                    await log_audit_event(
                        db=db,
                        tenant_id=effective_tenant,
                        event_type="rollback_plan_registered",
                        invocation_id=invocation.id,
                        agent_id=agent.agent_id if agent else None,
                        agent_tool_id=tool.id,
                        details={"rollback_action_id": rollback_action.id}
                    )

            # 6. Execute in Sandbox if enabled
            if settings.agent_tool_sandbox_enabled:
                output = await execute_in_sandbox(
                    db=db,
                    tenant_id=effective_tenant,
                    invocation_id=invocation.id,
                    tool_name=tool.name,
                    tool_category=tool.category,
                    parameters=modified_parameters,
                    allowed_commands=["*"], # Allow registry defined or * by default
                    timeout_seconds=int(tool.timeout_seconds),
                    tool_callable=effective_tool_callable
                )
            else:
                if effective_tool_callable is not None:
                    # Enforce programmatic timeout outside sandbox
                    if asyncio.iscoroutinefunction(effective_tool_callable):
                        output = await asyncio.wait_for(
                            effective_tool_callable(**modified_parameters),
                            timeout=float(tool.timeout_seconds)
                        )
                    else:
                        def sync_wrapper():
                            return effective_tool_callable(**modified_parameters)
                        output = await asyncio.wait_for(
                            asyncio.to_thread(sync_wrapper),
                            timeout=float(tool.timeout_seconds)
                        )
                else:
                    output = {"status": "success", "message": f"Simulated execution of tool {tool.name}"}

        invocation.output_hash = hash_payload(output)
        await log_audit_event(
            db=db,
            tenant_id=effective_tenant,
            event_type="tool_invocation_completed",
            invocation_id=invocation.id,
            agent_id=agent.agent_id if agent else None,
            agent_tool_id=tool.id,
            decision="success",
            details={"output": output}
        )

    except (asyncio.TimeoutError, Exception) as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        invocation.latency_ms = latency_ms
        invocation.status = "failed"
        invocation.error_message = str(e) or type(e).__name__
        
        await log_audit_event(
            db=db,
            tenant_id=effective_tenant,
            event_type="tool_invocation_failed",
            invocation_id=invocation.id,
            agent_id=agent.agent_id if agent else None,
            agent_tool_id=tool.id,
            decision="failed",
            reason=str(e),
            details={"error_class": type(e).__name__}
        )
        
        # Rollback / Compensation if supported and enabled
        if tool.rollback_supported and settings.agent_tool_rollback_enabled:
            try:
                rolled_back = await rollback_invocation_side_effects(
                    db=db,
                    tenant_id=effective_tenant,
                    invocation_id=invocation.id,
                    rollback_callable=effective_rollback_callable
                )
                if rolled_back:
                    invocation.status = "rolled_back"
                    await log_audit_event(
                        db=db,
                        tenant_id=effective_tenant,
                        event_type="rollback_executed",
                        invocation_id=invocation.id,
                        agent_id=agent.agent_id if agent else None,
                        agent_tool_id=tool.id,
                        decision="success",
                        reason="Automatic compensation completed successfully."
                    )
            except Exception as rollback_err:
                logger.error(f"Rollback failed for tool {tool.name}: {rollback_err}")
                invocation.error_message += f" | Rollback failed: {rollback_err}"
                await log_audit_event(
                    db=db,
                    tenant_id=effective_tenant,
                    event_type="rollback_failed",
                    invocation_id=invocation.id,
                    agent_id=agent.agent_id if agent else None,
                    agent_tool_id=tool.id,
                    decision="failed",
                    reason=str(rollback_err)
                )
        
        await db.commit()
        raise e

    latency_ms = int((time.monotonic() - start_time) * 1000)
    invocation.latency_ms = latency_ms
    await db.commit()
    
    return output
