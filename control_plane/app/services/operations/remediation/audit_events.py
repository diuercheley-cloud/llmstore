import uuid
import hashlib
import json
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_action_log import AdminActionLog
from app.core.time import utc_now

async def log_remediation_audit_event(
    session: AsyncSession,
    action: str,
    client_id: uuid.UUID,
    payload: Dict[str, Any],
    status: str = "success"
):
    """
    Logs a remediation audit event to the AdminActionLog.
    Follows offline-compatible and advisory-only rules.
    """
    sanitized_payload = {k: v for k, v in payload.items() if not k.startswith("_")}
    sanitized_payload["client_id"] = str(client_id)
    sanitized_payload["advisory_only"] = True
    
    signature_material = json.dumps(
        {"action": action, "client_id": str(client_id), "payload": sanitized_payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    sanitized_payload["signature"] = hashlib.sha256(signature_material.encode("utf-8")).hexdigest()[:16]

    audit_entry = AdminActionLog(
        action=f"ops_remediation:{action}",
        admin_role="system",
        request_path="/internal/operations/remediation",
        request_method="SYSTEM",
        payload_json=sanitized_payload,
        status=status,
        created_at=utc_now()
    )
    
    session.add(audit_entry)
    return audit_entry

async def log_remediation_plan_proposed(session: AsyncSession, client_id: uuid.UUID, plan_id: uuid.UUID, plan_type: str):
    return await log_remediation_audit_event(
        session,
        "remediation_plan_proposed",
        client_id,
        {"plan_id": str(plan_id), "plan_type": plan_type}
    )

async def log_remediation_step_proposed(session: AsyncSession, client_id: uuid.UUID, step_id: uuid.UUID, action_type: str):
    return await log_remediation_audit_event(
        session,
        "remediation_step_proposed",
        client_id,
        {"step_id": str(step_id), "action_type": action_type}
    )

async def log_remediation_approval_required(session: AsyncSession, client_id: uuid.UUID, plan_id: uuid.UUID, approval_scope: str):
    return await log_remediation_audit_event(
        session,
        "remediation_approval_required",
        client_id,
        {"plan_id": str(plan_id), "approval_scope": approval_scope}
    )

async def log_remediation_plan_receipt_created(session: AsyncSession, client_id: uuid.UUID, receipt_id: uuid.UUID, plan_id: uuid.UUID):
    return await log_remediation_audit_event(
        session,
        "remediation_plan_receipt_created",
        client_id,
        {"receipt_id": str(receipt_id), "plan_id": str(plan_id)}
    )
