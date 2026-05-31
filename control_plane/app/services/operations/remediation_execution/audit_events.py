import uuid
import hashlib
import json
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_action_log import AdminActionLog
from app.core.time import utc_now

async def log_remediation_execution_audit_event(
    session: AsyncSession,
    action: str,
    client_id: uuid.UUID,
    payload: Dict[str, Any],
    status: str = "success"
):
    """
    Logs a remediation execution audit event to the AdminActionLog.
    Offline-compatible and sanitized.
    """
    sanitized_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    sanitized_payload["client_id"] = str(client_id)
    
    signature_material = json.dumps(
        {"action": action, "client_id": str(client_id), "payload": sanitized_payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    sanitized_payload["signature"] = hashlib.sha256(signature_material.encode("utf-8")).hexdigest()[:16]

    audit_entry = AdminActionLog(
        action=f"ops_remediation_exec:{action}",
        admin_role="system",
        request_path="/internal/operations/remediation-execution",
        request_method="SYSTEM",
        payload_json=sanitized_payload,
        status=status,
        created_at=utc_now()
    )
    
    session.add(audit_entry)
    return audit_entry

async def log_remediation_execution_prepared(session: AsyncSession, client_id: uuid.UUID, execution_id: uuid.UUID, plan_id: uuid.UUID):
    return await log_remediation_execution_audit_event(
        session, "remediation_execution_prepared", client_id, {"execution_id": str(execution_id), "plan_id": str(plan_id)}
    )

async def log_remediation_execution_started(session: AsyncSession, client_id: uuid.UUID, execution_id: uuid.UUID):
    return await log_remediation_execution_audit_event(
        session, "remediation_execution_started", client_id, {"execution_id": str(execution_id)}
    )


async def log_remediation_execution_step_executed(session: AsyncSession, client_id: uuid.UUID, step_id: uuid.UUID, status: str):
    return await log_remediation_execution_audit_event(
        session, "remediation_execution_step_executed", client_id, {"step_id": str(step_id), "status": status}
    )

async def log_remediation_execution_step_simulated(session: AsyncSession, client_id: uuid.UUID, step_id: uuid.UUID, status: str):
    return await log_remediation_execution_audit_event(
        session, "remediation_execution_step_simulated", client_id, {"step_id": str(step_id), "status": status}
    )

async def log_remediation_execution_completed(session: AsyncSession, client_id: uuid.UUID, execution_id: uuid.UUID):
    return await log_remediation_execution_audit_event(
        session, "remediation_execution_completed", client_id, {"execution_id": str(execution_id)}
    )

async def log_remediation_execution_killed(session: AsyncSession, client_id: uuid.UUID, execution_id: uuid.UUID, reason: str):
    return await log_remediation_execution_audit_event(
        session, "remediation_execution_killed", client_id, {"execution_id": str(execution_id), "reason": reason}
    )

async def log_remediation_kill_switch_updated(session: AsyncSession, client_id: uuid.UUID, enabled: bool, reason: str):
    return await log_remediation_execution_audit_event(
        session, "remediation_kill_switch_updated", client_id, {"enabled": enabled, "reason": reason}
    )
