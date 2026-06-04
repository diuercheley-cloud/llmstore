# Owner: agent-platform
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import (
    AgentApprovalDecision,
    AgentApprovalPolicy,
    AgentApprovalRequest,
    AgentRegistryEntry,
    AgentRun,
    AgentTool,
)
from app.services.admin_rbac import record_admin_audit_event
from app.services.auth import AdminRole
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def sanitize_value(val: Any) -> Any:
    """Recursively redacts sensitive values and truncates long strings to protect data privacy."""
    if isinstance(val, dict):
        return {
            k: sanitize_value(v)
            if not any(x in k.lower() for x in ("prompt", "secret", "token", "password", "key", "auth", "instructions", "credential", "signature", "private"))
            else "<redacted>"
            for k, v in val.items()
        }
    elif isinstance(val, list):
        return [sanitize_value(item) for item in val]
    elif isinstance(val, str):
        if len(val) > 500:
            return val[:500] + f"... [truncated, original length: {len(val)}]"
        return val
    return val


def has_sufficient_role(caller_role: AdminRole, required_role_str: str) -> bool:
    """Compares current caller admin role against the request's required reviewer role."""
    req_clean = required_role_str.lower().strip()
    if req_clean in ("super_admin", "superadmin", "super"):
        req_enum = AdminRole.SUPER
    elif req_clean in ("admin_write", "write"):
        req_enum = AdminRole.WRITE
    else:
        req_enum = AdminRole.READ
    return caller_role >= req_enum


async def check_approval_required(
    db: AsyncSession,
    run_id: uuid.UUID,
    tool_name: str,
    tool_input: dict
) -> Tuple[bool, str, str, str]:
    """
    Evaluates policies, registry status, and feature flags to check if approval is required.
    Returns:
        (approval_required, risk_level, reason, required_role)
    """
    from app.services.agents import agent_state

    settings = get_settings()
    if not settings.agent_human_approval_enabled:
        return False, "low", "HITL is disabled globally", "admin_write"

    run = await agent_state.get_agent_run(db, run_id)
    if not run:
        return False, "low", "Run not found", "admin_write"

    agent_def = await agent_state.get_agent_definition(db, run.agent_id)
    if not agent_def:
        return False, "low", "Agent definition not found", "admin_write"

    agent_risk = (agent_def.risk_level or "low").lower()

    # Check agent registry entry risk level
    registry_risk = "low"
    registry_approval_required = False
    stmt_reg = select(AgentRegistryEntry).where(AgentRegistryEntry.agent_id == run.agent_id)
    reg_res = await db.execute(stmt_reg)
    registry_entry = reg_res.scalar_one_or_none()
    if registry_entry:
        registry_risk = (registry_entry.risk_level or "low").lower()
        registry_approval_required = registry_entry.human_approval_required

    # Check tool registry
    tool_risk = "low"
    tool_requires_approval = False
    tool_side_effect = "none"
    stmt_t = select(AgentTool).where(AgentTool.name == tool_name)
    t_res = await db.execute(stmt_t)
    tool_entry = t_res.scalar_one_or_none()
    if tool_entry:
        tool_risk = (tool_entry.risk_level or "low").lower()
        tool_requires_approval = tool_entry.requires_approval
        tool_side_effect = (tool_entry.side_effect_level or "none").lower()

    # Defaults for side effect level
    if tool_side_effect in ("write", "destructive"):
        tool_requires_approval = True

    # Calculate overall risk
    RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    max_risk_str = "low"
    max_risk_val = 1
    for r in (agent_risk, registry_risk, tool_risk):
        val = RISK_ORDER.get(r, 1)
        if val > max_risk_val:
            max_risk_val = val
            max_risk_str = r

    # 1. Evaluate Agent Approval Policies
    stmt_p = select(AgentApprovalPolicy).where(AgentApprovalPolicy.enabled == True)
    p_res = await db.execute(stmt_p)
    policies = p_res.scalars().all()

    for policy in policies:
        triggered = False
        if policy.trigger_type == "always":
            triggered = True
        elif policy.trigger_type == "tool_call" and policy.tool_name == tool_name:
            triggered = True
        elif policy.trigger_type == "risk_level" and policy.risk_level_threshold:
            thresh_val = RISK_ORDER.get(policy.risk_level_threshold.lower(), 1)
            if max_risk_val >= thresh_val:
                triggered = True

        if triggered:
            return True, max_risk_str, f"Policy match: {policy.name}", policy.required_role or "admin_write"

    # 2. Check registry lifecycle and explicit tool overrides
    if registry_approval_required:
        return True, max_risk_str, "Agent lifecycle requires human approval", "admin_write"

    if tool_requires_approval:
        return True, max_risk_str, f"Tool '{tool_name}' requires approval", "admin_write"

    # Notification sensitive keywords approval policy
    if tool_name in ("notify_email", "notify_push"):
        from app.services.notifications.notification_policy import has_sensitive_keywords
        title = tool_input.get("title", "")
        body = tool_input.get("body", "")
        if has_sensitive_keywords(title, body):
            return True, "medium", f"Notification tool '{tool_name}' has sensitive keywords", "admin_write"

    # 3. High risk threshold rule
    if settings.agent_approval_required_for_high_risk:
        if max_risk_str in ("high", "critical"):
            role = "super_admin" if max_risk_str == "critical" else "admin_write"
            return True, max_risk_str, f"Mandatory approval for risk level: {max_risk_str}", role

    return False, max_risk_str, "No approval required", "admin_write"


async def create_approval_request(
    db: AsyncSession,
    run_id: uuid.UUID,
    tool_name: str,
    tool_input: dict,
    risk_level: str,
    reason: str,
    required_role: str,
    step_number: int,
    task_id: Optional[str] = None,
    tool_invocation_id: Optional[uuid.UUID] = None
) -> AgentApprovalRequest:
    """Creates a pending AgentApprovalRequest in the database."""
    settings = get_settings()
    expires_at = utc_now() + timedelta(seconds=settings.agent_approval_timeout_seconds)

    sanitized_context = {
        "tool_name": tool_name,
        "step_number": step_number,
        "tool_input": sanitize_value(tool_input),
    }

    req = AgentApprovalRequest(
        agent_run_id=run_id,
        task_id=task_id,
        tool_invocation_id=tool_invocation_id,
        risk_level=risk_level,
        reason=reason,
        requested_by="agent_executor",
        reviewer_role=required_role,
        status="pending",
        expires_at=expires_at,
        sanitized_context=sanitized_context,
        raw_tool_input=tool_input,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    logger.info(f"Created AgentApprovalRequest: {req.id} for run {run_id}")
    return req

async def check_and_apply_expiration(db: AsyncSession, request: AgentApprovalRequest) -> bool:
    """Fails safe if a request is expired."""
    expires_at = _as_utc_aware(request.expires_at)

    if request.status == "pending" and expires_at and expires_at < utc_now():
        request.status = "expired"
        request.updated_at = utc_now()

        decision = AgentApprovalDecision(
            approval_request_id=request.id,
            decision="expired",
            reason="Approval request timed out / expired",
            decided_by="system",
            decided_at=utc_now()
        )
        db.add(decision)

        # Update the run to failed
        stmt_run = select(AgentRun).where(AgentRun.id == request.agent_run_id)
        run_res = await db.execute(stmt_run)
        run = run_res.scalar_one_or_none()
        if run and run.status == "waiting_approval":
            run.status = "failed"
            run.failure_reason = "Approval request expired"
            run.completed_at = utc_now()
            
            # Log run event
            from app.services.agents import agent_state
            await agent_state.log_run_event(db, run.id, "run_failed", {"reason": "approval_expired"})

        await db.commit()
        logger.info(f"AgentApprovalRequest {request.id} expired. Associated run {request.agent_run_id} marked as failed.")
        return True
    return False


async def check_all_expired_requests(db: AsyncSession) -> None:
    """Scans and updates all pending expired requests in the database."""
    stmt = select(AgentApprovalRequest).where(
        AgentApprovalRequest.status == "pending",
        AgentApprovalRequest.expires_at < utc_now()
    )
    res = await db.execute(stmt)
    expired_reqs = res.scalars().all()
    for req in expired_reqs:
        await check_and_apply_expiration(db, req)


async def approve_approval_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    decided_by: str,
    caller_role: AdminRole,
    reason: Optional[str] = None
) -> AgentApprovalRequest:
    """Approves request, logs decision and audit, and resumes execution."""
    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == request_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError(f"Approval request {request_id} not found")

    # 1. Expiration check
    is_expired = await check_and_apply_expiration(db, req)
    if is_expired or req.status != "pending":
        raise ValueError(f"Cannot approve request in status: {req.status}")

    # 2. Role permission check
    if not has_sufficient_role(caller_role, req.reviewer_role):
        raise ValueError("insufficient_reviewer_role")

    # 3. Transition status
    req.status = "approved"
    req.decision_reason = reason
    req.decided_by = decided_by
    req.decided_at = utc_now()
    req.updated_at = utc_now()

    # 4. Log decision
    decision = AgentApprovalDecision(
        approval_request_id=req.id,
        decision="approved",
        reason=reason,
        decided_by=decided_by,
        decided_at=utc_now()
    )
    db.add(decision)

    # 4.5 Resolve associated run before metrics/resume.
    from app.services.agents import agent_state
    run = await agent_state.get_agent_run(db, req.agent_run_id)
    if not run:
        raise ValueError(f"Agent run {req.agent_run_id} not found")

    # Record metrics
    from app.services.agents.agent_observability import AgentObservabilityService
    obs = AgentObservabilityService(db)
    wait_time = (utc_now() - _as_utc_aware(req.created_at)).total_seconds()
    tool_name = (req.sanitized_context or {}).get("tool_name")
    await obs.record_approval_wait(run.agent_id, run.id, tool_name, wait_time)

    # Audit log
    await record_admin_audit_event(
        db,
        event_type="agent.approval.approved",
        status="success",
        actor_identifier=decided_by,
        target_type="agent_approval_request",
        target_id=str(req.id),
        metadata={"agent_run_id": str(run.id), "reason": reason}
    )

    await db.commit()
    await db.refresh(req)

    # We resume the run using the runtime executor orchestration
    from app.services.agents.agent_runtime import resume_run_internal
    await resume_run_internal(db, run.id)

    return req


async def reject_approval_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    decided_by: str,
    caller_role: AdminRole,
    reason: Optional[str] = None
) -> AgentApprovalRequest:
    """Rejects request, logs decision and audit, and terminates run execution."""
    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == request_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError(f"Approval request {request_id} not found")

    # 1. Expiration check
    is_expired = await check_and_apply_expiration(db, req)
    if is_expired or req.status != "pending":
        raise ValueError(f"Cannot reject request in status: {req.status}")

    # 2. Role permission check
    if not has_sufficient_role(caller_role, req.reviewer_role):
        raise ValueError("insufficient_reviewer_role")

    # 3. Transition status
    req.status = "rejected"
    req.decision_reason = reason
    req.decided_by = decided_by
    req.decided_at = utc_now()
    req.updated_at = utc_now()

    # 4. Log decision
    decision = AgentApprovalDecision(
        approval_request_id=req.id,
        decision="rejected",
        reason=reason,
        decided_by=decided_by,
        decided_at=utc_now()
    )
    db.add(decision)

    # 4.5 Resolve associated run before metrics/termination.
    from app.services.agents import agent_state
    run = await agent_state.get_agent_run(db, req.agent_run_id)

    # Record metrics
    from app.services.agents.agent_observability import AgentObservabilityService
    obs = AgentObservabilityService(db)
    wait_time = (utc_now() - _as_utc_aware(req.created_at)).total_seconds()
    tool_name = (req.sanitized_context or {}).get("tool_name")
    if run:
        await obs.record_approval_wait(run.agent_id, run.id, tool_name, wait_time)

    # 5. Terminate the run execution
    if run:
        run.status = "failed"
        run.failure_reason = f"Approval request rejected: {reason or 'No reason provided'}"
        run.completed_at = utc_now()
        await agent_state.log_run_event(db, run.id, "run_failed", {"reason": "approval_rejected", "details": reason})

    # Audit log
    await record_admin_audit_event(
        db,
        event_type="agent.approval.rejected",
        status="success",
        actor_identifier=decided_by,
        target_type="agent_approval_request",
        target_id=str(req.id),
        metadata={"agent_run_id": str(req.agent_run_id), "reason": reason}
    )

    await db.commit()
    await db.refresh(req)
    return req


async def request_changes_for_approval_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    decided_by: str,
    caller_role: AdminRole,
    reason: Optional[str] = None
) -> AgentApprovalRequest:
    """Requests changes, transitions request to cancelled, and pauses run execution."""
    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == request_id)
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if not req:
        raise ValueError(f"Approval request {request_id} not found")

    # 1. Expiration check
    is_expired = await check_and_apply_expiration(db, req)
    if is_expired or req.status != "pending":
        raise ValueError(f"Cannot request changes in status: {req.status}")

    # 2. Role permission check
    if not has_sufficient_role(caller_role, req.reviewer_role):
        raise ValueError("insufficient_reviewer_role")

    # 3. Transition status
    req.status = "cancelled"
    req.decision_reason = reason
    req.decided_by = decided_by
    req.decided_at = utc_now()
    req.updated_at = utc_now()

    # 4. Log decision
    decision = AgentApprovalDecision(
        approval_request_id=req.id,
        decision="request_changes",
        reason=reason,
        decided_by=decided_by,
        decided_at=utc_now()
    )
    db.add(decision)

    # 5. Pause the run
    from app.services.agents import agent_state
    run = await agent_state.get_agent_run(db, req.agent_run_id)
    if run:
        run.status = "paused"
        await agent_state.log_run_event(db, run.id, "run_paused", {"reason": "changes_requested", "details": reason})

    # Audit log
    await record_admin_audit_event(
        db,
        event_type="agent.approval.request_changes",
        status="success",
        actor_identifier=decided_by,
        target_type="agent_approval_request",
        target_id=str(req.id),
        metadata={"agent_run_id": str(req.agent_run_id), "reason": reason}
    )

    await db.commit()
    await db.refresh(req)
    return req
