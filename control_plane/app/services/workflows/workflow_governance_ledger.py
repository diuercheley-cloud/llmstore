from __future__ import annotations

from typing import Any

from app.core.time import utc_now
from app.models.commercial.commercial_workflows import (
    CommercialWorkflowExecution,
    CommercialWorkflowGovernanceEvent,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.workflows.workflow_provenance import redact_sensitive_payload, sha256_hex
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

VALID_GOVERNANCE_EVENTS = {
    "workflow_started",
    "stage_policy_bound",
    "approval_requested",
    "approval_granted",
    "approval_rejected",
    "replay_started",
    "replay_completed",
    "drift_detected",
    "policy_override",
    "workflow_rolled_back",
}


def sanitize_actor_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    payload = redact_sensitive_payload(metadata or {})
    payload.pop("token", None)
    payload.pop("authorization", None)
    payload.pop("api_key", None)
    return sanitize_report_payload(payload)


def sign_governance_payload(payload: Any, *, scope: str) -> str:
    digest = sha256_hex({"scope": scope, "payload": payload})
    return f"ed25519:{digest[:48]}"


class WorkflowGovernanceLedgerService:
    async def append_event(
        self,
        db: AsyncSession,
        *,
        execution: CommercialWorkflowExecution,
        event_type: str,
        tenant_id: str | None = None,
        stage_id=None,
        replay_session_id=None,
        actor_id: str | None = None,
        actor_metadata: dict[str, Any] | None = None,
        event_summary: str | None = None,
        event_payload: dict[str, Any] | None = None,
    ) -> CommercialWorkflowGovernanceEvent:
        if event_type not in VALID_GOVERNANCE_EVENTS:
            raise ValueError(f"unsupported_governance_event:{event_type}")
        previous = (
            await db.execute(
                select(CommercialWorkflowGovernanceEvent)
                .where(CommercialWorkflowGovernanceEvent.execution_id == execution.id)
                .order_by(desc(CommercialWorkflowGovernanceEvent.created_at), desc(CommercialWorkflowGovernanceEvent.id))
                .limit(1)
            )
        ).scalar_one_or_none()
        sanitized_actor_metadata = sanitize_actor_metadata(actor_metadata)
        sanitized_payload = sanitize_report_payload(redact_sensitive_payload(event_payload or {}))
        created_at = utc_now()
        event_hash = sha256_hex(
            {
                "execution_id": str(execution.id),
                "stage_id": str(stage_id) if stage_id else None,
                "replay_session_id": str(replay_session_id) if replay_session_id else None,
                "event_type": event_type,
                "actor_id": actor_id,
                "actor_metadata": sanitized_actor_metadata,
                "event_summary": event_summary,
                "event_payload": sanitized_payload,
                "previous_event_hash": previous.event_hash if previous else None,
                "created_at": created_at.isoformat(),
            }
        )
        ledger_hash = sha256_hex(
            {
                "previous_ledger_hash": previous.ledger_hash if previous else execution.governance_ledger_hash,
                "event_hash": event_hash,
            }
        )
        row = CommercialWorkflowGovernanceEvent(
            execution_id=execution.id,
            stage_id=stage_id,
            replay_session_id=replay_session_id,
            tenant_id=tenant_id or execution.tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_metadata_json=sanitized_actor_metadata,
            event_summary=event_summary,
            event_payload_json=sanitized_payload,
            previous_event_hash=previous.event_hash if previous else None,
            event_hash=event_hash,
            ledger_hash=ledger_hash,
            detached_signature=sign_governance_payload(sanitized_payload, scope=event_type),
            signature_algorithm="ed25519",
            created_at=created_at,
        )
        db.add(row)
        execution.governance_ledger_hash = ledger_hash
        await db.flush()
        return row

    async def validate_ledger(
        self,
        db: AsyncSession,
        *,
        execution_id,
    ) -> dict[str, Any]:
        rows = (
            await db.execute(
                select(CommercialWorkflowGovernanceEvent)
                .where(CommercialWorkflowGovernanceEvent.execution_id == execution_id)
                .order_by(CommercialWorkflowGovernanceEvent.created_at.asc(), CommercialWorkflowGovernanceEvent.id.asc())
            )
        ).scalars().all()
        previous_event_hash = None
        previous_ledger_hash = None
        issues: list[str] = []
        for row in rows:
            if row.previous_event_hash != previous_event_hash:
                issues.append(f"event_chain_break:{row.event_type}:{row.id}")
            expected_ledger_hash = sha256_hex(
                {
                    "previous_ledger_hash": previous_ledger_hash,
                    "event_hash": row.event_hash,
                }
            )
            if row.ledger_hash != expected_ledger_hash:
                issues.append(f"ledger_hash_invalid:{row.event_type}:{row.id}")
            previous_event_hash = row.event_hash
            previous_ledger_hash = row.ledger_hash
        return {"valid": not issues, "count": len(rows), "issues": issues}

    async def list_events(
        self,
        db: AsyncSession,
        *,
        execution_id,
    ) -> list[CommercialWorkflowGovernanceEvent]:
        return (
            await db.execute(
                select(CommercialWorkflowGovernanceEvent)
                .where(CommercialWorkflowGovernanceEvent.execution_id == execution_id)
                .order_by(CommercialWorkflowGovernanceEvent.created_at.asc(), CommercialWorkflowGovernanceEvent.id.asc())
            )
        ).scalars().all()
