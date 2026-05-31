import uuid
import hashlib
import json
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_action_log import AdminActionLog
from app.core.time import utc_now

async def log_adapter_sandbox_audit_event(
    session: AsyncSession,
    action: str,
    client_id: uuid.UUID,
    payload: Dict[str, Any],
    status: str = "success"
):
    """
    Logs an adapter sandbox audit event to the AdminActionLog.
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
        action=f"ops_adapter_sandbox:{action}",
        admin_role="system",
        request_path="/internal/operations/adapter-sandbox",
        request_method="SYSTEM",
        payload_json=sanitized_payload,
        status=status,
        created_at=utc_now()
    )
    
    session.add(audit_entry)
    return audit_entry

async def log_adapter_manifest_registered(session: AsyncSession, client_id: uuid.UUID, manifest_id: uuid.UUID, adapter_name: str):
    return await log_adapter_sandbox_audit_event(
        session, "adapter_manifest_registered", client_id, {"manifest_id": str(manifest_id), "adapter_name": adapter_name}
    )

async def log_adapter_manifest_blocked(session: AsyncSession, client_id: uuid.UUID, manifest_id: uuid.UUID, reason: str):
    return await log_adapter_sandbox_audit_event(
        session, "adapter_manifest_blocked", client_id, {"manifest_id": str(manifest_id), "reason": reason}, status="blocked"
    )

async def log_adapter_sandbox_run_prepared(session: AsyncSession, client_id: uuid.UUID, run_id: uuid.UUID):
    return await log_adapter_sandbox_audit_event(
        session, "adapter_sandbox_run_prepared", client_id, {"run_id": str(run_id)}
    )

async def log_adapter_sandbox_run_completed(session: AsyncSession, client_id: uuid.UUID, run_id: uuid.UUID, status: str):
    return await log_adapter_sandbox_audit_event(
        session, "adapter_sandbox_run_completed", client_id, {"run_id": str(run_id), "status": status}
    )

async def log_adapter_policy_violation_detected(session: AsyncSession, client_id: uuid.UUID, violation_id: uuid.UUID, v_type: str):
    return await log_adapter_sandbox_audit_event(
        session, "adapter_policy_violation_detected", client_id, {"violation_id": str(violation_id), "type": v_type}, status="violation"
    )
