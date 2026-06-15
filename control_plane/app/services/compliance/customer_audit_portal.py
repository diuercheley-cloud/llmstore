from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing.billing_invoice import BillingInvoice
from app.models.commercial.commercial_audit_portal import (
    CommercialPortalAuditAccessLog,
    CommercialPortalSavedReport,
)
from app.models.commercial.commercial_billing_dispute import CommercialBillingDispute
from app.models.commercial.commercial_compliance import (
    CommercialApprovalChain,
    CommercialControlAttestation,
    CommercialControlException,
    CommercialControlPolicy,
    CommercialEvidencePackage,
    CommercialOperationalControl,
    CommercialOperationalEvidence,
    CommercialOperationalExceptionLink,
    CommercialOperationalReview,
)
from app.models.commercial.commercial_financial_audit_event import CommercialFinancialAuditEvent
from app.models.commercial.commercial_financial_reconciliation import (
    CommercialFinancialReconciliation,
)
from app.models.commercial.commercial_qos_billing_record import CommercialQoSBillingRecord
from app.models.core.client import Client
from app.services.routing.commercial_report_export import (
    SECRET_VALUE_PATTERNS,
    sanitize_report_payload,
)
from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

EXPORT_WATERMARK = "CONFIDENTIAL ENTERPRISE AUDIT EXPORT"
UA_LIMIT = 255
TEXT_LIMIT = 255
_EMAIL_RE = re.compile(r"[^a-zA-Z0-9@._+-]")
_DROP_KEYS = {
    "api_key",
    "api_keys",
    "authorization",
    "prompt",
    "prompts",
    "response",
    "responses",
    "secret",
    "secrets",
    "smtp_secret",
    "smtp_password",
    "provider_secret",
    "provider_secrets",
    "webhook_secret",
}


@dataclass
class PortalActor:
    actor_id: uuid.UUID | None
    actor_email: str | None
    actor_name: str | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _exports_root() -> Path:
    root = _repo_root() / "artifacts" / "enterprise-audit-exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _to_utc_datetime(value: date | datetime | None, *, end_of_day: bool = False) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    clock = time.max if end_of_day else time.min
    return datetime.combine(value, clock, tzinfo=UTC)


def _sanitize_email(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _EMAIL_RE.sub("", value.strip())
    return cleaned[:TEXT_LIMIT] or None


def _sanitize_text(value: str | None, *, limit: int = TEXT_LIMIT) -> str | None:
    if not value:
        return None
    sanitized = value.replace("\r", " ").replace("\n", " ").strip()
    for pattern in SECRET_VALUE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized[:limit] or None


def _sanitize_json(value: Any) -> dict[str, Any]:
    def _drop_secret_keys(node: Any) -> Any:
        if isinstance(node, dict):
            cleaned: dict[str, Any] = {}
            for key, child in node.items():
                lowered = str(key).lower()
                if lowered in _DROP_KEYS:
                    continue
                cleaned[str(key)] = _drop_secret_keys(child)
            return cleaned
        if isinstance(node, list):
            return [_drop_secret_keys(item) for item in node]
        return node

    sanitized = sanitize_report_payload(_drop_secret_keys(value or {}))
    return sanitized if isinstance(sanitized, dict) else {"value": sanitized}


def _mask_ip(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    value = ip_address.strip()
    if ":" in value:
        parts = value.split(":")
        head = ":".join(parts[:3])
        return f"{head}:****" if head else "****"
    octets = value.split(".")
    if len(octets) == 4:
        return ".".join([octets[0], octets[1], octets[2], "x"])
    if len(value) <= 2:
        return "x"
    return f"{value[:2]}***"


def _hash_payload(payload: Any) -> str:
    body = json.dumps(
        sanitize_report_payload(payload), sort_keys=True, ensure_ascii=True, default=str
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _infer_actor(
    client: Client,
    actor_id: str | None = None,
    actor_email: str | None = None,
    actor_name: str | None = None,
) -> PortalActor:
    parsed_actor_id: uuid.UUID | None = None
    if actor_id:
        try:
            parsed_actor_id = uuid.UUID(str(actor_id))
        except ValueError:
            parsed_actor_id = None

    metadata: dict[str, Any] = {}
    if client.metadata_json:
        try:
            raw = json.loads(client.metadata_json)
            if isinstance(raw, dict):
                metadata = raw
        except json.JSONDecodeError:
            metadata = {}

    return PortalActor(
        actor_id=parsed_actor_id,
        actor_email=_sanitize_email(actor_email or metadata.get("contact_email")),
        actor_name=_sanitize_text(actor_name or metadata.get("contact_name")),
    )


def validate_portal_resource_access(
    *,
    client_id: uuid.UUID,
    resource_client_id: uuid.UUID | None,
    resource_type: str,
    resource_id: uuid.UUID | str | None = None,
) -> None:
    if resource_client_id is None or resource_client_id != client_id:
        raise HTTPException(
            status_code=404,
            detail=f"{resource_type} not found",
        )


def _build_time_filters(
    column,
    *,
    period_start: date | datetime | None,
    period_end: date | datetime | None,
) -> list[Any]:
    clauses: list[Any] = []
    start_dt = _to_utc_datetime(period_start, end_of_day=False)
    end_dt = _to_utc_datetime(period_end, end_of_day=True)
    if start_dt is not None:
        clauses.append(column >= start_dt)
    if end_dt is not None:
        clauses.append(column <= end_dt)
    return clauses


def _build_date_overlap_filters(
    start_column,
    end_column,
    *,
    period_start: date | None,
    period_end: date | None,
) -> list[Any]:
    clauses: list[Any] = []
    if period_start is not None:
        clauses.append(end_column >= period_start)
    if period_end is not None:
        clauses.append(start_column <= period_end)
    return clauses


def _serialize_policy(policy: CommercialControlPolicy | None) -> dict[str, Any] | None:
    if policy is None:
        return None
    return {
        "id": str(policy.id),
        "name": policy.name,
        "control_area": policy.control_area,
        "action_type": policy.action_type,
        "requires_approval": policy.requires_approval,
        "evidence_required": policy.evidence_required,
    }


def _serialize_approval_chain(item: CommercialApprovalChain) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "client_id": str(item.client_id) if item.client_id else None,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "status": item.status,
            "requested_by": _sanitize_text(item.requested_by),
            "required_approver_count": item.required_approver_count,
            "approvals_json": item.approvals_json or [],
            "rejections_json": item.rejections_json or [],
            "evidence_package_id": str(item.evidence_package_id)
            if item.evidence_package_id
            else None,
            "control_policy": _serialize_policy(item.policy),
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "decided_at": item.decided_at.isoformat() if item.decided_at else None,
        }
    )


def _serialize_evidence_package(item: CommercialEvidencePackage) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "client_id": str(item.client_id) if item.client_id else None,
            "package_type": item.package_type,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "summary": _sanitize_text(item.summary, limit=1000),
            "evidence_json": item.evidence_json or {},
            "file_refs_json": item.file_refs_json or {},
            "immutable_hash": item.immutable_hash,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
    )


def _serialize_attestation(item: CommercialControlAttestation) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "client_id": str(item.client_id) if item.client_id else None,
            "control_policy_id": str(item.control_policy_id),
            "status": item.status,
            "attested_by": _sanitize_text(item.attested_by),
            "notes": _sanitize_text(item.notes, limit=1000),
            "evidence_package_id": str(item.evidence_package_id)
            if item.evidence_package_id
            else None,
            "period_start": item.attestation_period_start.isoformat(),
            "period_end": item.attestation_period_end.isoformat(),
            "attested_at": item.attested_at.isoformat() if item.attested_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "control_policy": _serialize_policy(item.policy),
        }
    )


def _serialize_exception(item: CommercialControlException) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "client_id": str(item.client_id) if item.client_id else None,
            "control_policy_id": str(item.control_policy_id) if item.control_policy_id else None,
            "exception_type": item.exception_type,
            "severity": item.severity,
            "status": item.status,
            "description": _sanitize_text(item.description, limit=1000),
            "remediation_plan": _sanitize_text(item.remediation_plan, limit=1000),
            "owner": _sanitize_text(item.owner),
            "due_at": item.due_at.isoformat() if item.due_at else None,
            "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "control_policy": _serialize_policy(item.policy),
        }
    )


def _serialize_saved_report(item: CommercialPortalSavedReport) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "client_id": str(item.client_id),
        "report_type": item.report_type,
        "period_start": item.period_start.isoformat(),
        "period_end": item.period_end.isoformat(),
        "filters_json": sanitize_report_payload(item.filters_json or {}),
        "export_format": item.export_format,
        "generated_by": _sanitize_text(item.generated_by),
        "storage_ref": Path(item.storage_ref).name if item.storage_ref else None,
        "immutable_hash": item.immutable_hash,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
    }


def _serialize_access_log(item: CommercialPortalAuditAccessLog) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "client_id": str(item.client_id),
        "actor_id": str(item.actor_id) if item.actor_id else None,
        "actor_email": item.actor_email,
        "resource_type": item.resource_type,
        "resource_id": item.resource_id,
        "action": item.action,
        "ip_masked": item.ip_masked,
        "user_agent_sanitized": item.user_agent_sanitized,
        "metadata_json": sanitize_report_payload(item.metadata_json or {}),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _serialize_operational_control(
    item: CommercialOperationalControl, linked_exceptions: list[dict[str, Any]]
) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "control_code": item.control_code,
            "name": item.name,
            "category": item.category,
            "description": _sanitize_text(item.description, limit=1000),
            "owner_email": _sanitize_text(item.owner_email),
            "review_frequency": item.review_frequency,
            "effectiveness_score": item.effectiveness_score,
            "effectiveness_status": item.effectiveness_status,
            "evidence_sla_days": item.evidence_sla_days,
            "last_reviewed_at": item.last_reviewed_at.isoformat()
            if item.last_reviewed_at
            else None,
            "next_review_due_at": item.next_review_due_at.isoformat()
            if item.next_review_due_at
            else None,
            "enabled": item.enabled,
            "linked_exceptions": linked_exceptions,
            "metadata_json": item.metadata_json or {},
        }
    )


def _serialize_operational_evidence(item: CommercialOperationalEvidence) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "control_id": str(item.control_id),
            "evidence_type": item.evidence_type,
            "title": item.title,
            "summary": _sanitize_text(item.summary, limit=1000),
            "evidence_json": item.evidence_json or {},
            "immutable_hash": item.immutable_hash,
            "freshness_status": item.freshness_status,
            "collected_at": item.collected_at.isoformat() if item.collected_at else None,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
    )


def _serialize_operational_review(item: CommercialOperationalReview) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "control_id": str(item.control_id),
            "review_period_start": item.review_period_start.isoformat(),
            "review_period_end": item.review_period_end.isoformat(),
            "reviewed_by": _sanitize_text(item.reviewed_by),
            "status": item.status,
            "findings": _sanitize_text(item.findings, limit=1000),
            "recommendations": _sanitize_text(item.recommendations, limit=1000),
            "evidence_package_id": str(item.evidence_package_id)
            if item.evidence_package_id
            else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }
    )


async def _visible_operational_exception_links(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
) -> list[tuple[CommercialOperationalExceptionLink, CommercialControlException]]:
    rows = (
        await db.execute(
            select(CommercialOperationalExceptionLink, CommercialControlException)
            .join(
                CommercialControlException,
                CommercialOperationalExceptionLink.exception_id == CommercialControlException.id,
            )
            .where(CommercialControlException.client_id == client_id)
            .order_by(desc(CommercialOperationalExceptionLink.created_at))
        )
    ).all()
    return rows


async def list_customer_operational_controls(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    control_category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    rows = await _visible_operational_exception_links(db, client_id=client_id)
    grouped_links: dict[uuid.UUID, list[dict[str, Any]]] = {}
    for link, exception in rows:
        grouped_links.setdefault(link.control_id, []).append(
            {
                "exception_id": str(exception.id),
                "status": exception.status,
                "severity": exception.severity,
                "owner": _sanitize_text(exception.owner),
                "remediation_status": link.remediation_status,
                "linkage_reason": _sanitize_text(link.linkage_reason, limit=500),
            }
        )
    if not grouped_links:
        return []
    stmt = (
        select(CommercialOperationalControl)
        .where(CommercialOperationalControl.id.in_(list(grouped_links.keys())))
        .order_by(CommercialOperationalControl.control_code.asc())
        .limit(limit)
    )
    if control_category:
        stmt = stmt.where(CommercialOperationalControl.category == control_category)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_operational_control(item, grouped_links.get(item.id, [])) for item in items]


async def list_customer_operational_evidence(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    freshness_status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    rows = await _visible_operational_exception_links(db, client_id=client_id)
    control_ids = list({link.control_id for link, _ in rows})
    if not control_ids:
        return []
    stmt = (
        select(CommercialOperationalEvidence)
        .where(CommercialOperationalEvidence.control_id.in_(control_ids))
        .order_by(desc(CommercialOperationalEvidence.created_at))
        .limit(limit)
    )
    if freshness_status:
        stmt = stmt.where(CommercialOperationalEvidence.freshness_status == freshness_status)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_operational_evidence(item) for item in items]


async def list_customer_operational_reviews(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    rows = await _visible_operational_exception_links(db, client_id=client_id)
    control_ids = list({link.control_id for link, _ in rows})
    if not control_ids:
        return []
    stmt = (
        select(CommercialOperationalReview)
        .where(CommercialOperationalReview.control_id.in_(control_ids))
        .order_by(desc(CommercialOperationalReview.created_at))
        .limit(limit)
    )
    if status:
        stmt = stmt.where(CommercialOperationalReview.status == status)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_operational_review(item) for item in items]


async def list_customer_approval_chains(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(CommercialApprovalChain)
        .options(selectinload(CommercialApprovalChain.policy))
        .join(
            CommercialControlPolicy,
            CommercialApprovalChain.control_policy_id == CommercialControlPolicy.id,
        )
        .where(CommercialApprovalChain.client_id == client_id)
        .order_by(desc(CommercialApprovalChain.created_at))
        .limit(limit)
    )
    for clause in _build_time_filters(
        CommercialApprovalChain.created_at, period_start=period_start, period_end=period_end
    ):
        stmt = stmt.where(clause)
    if status:
        stmt = stmt.where(CommercialApprovalChain.status == status)
    if actor:
        stmt = stmt.where(CommercialApprovalChain.requested_by == actor)
    if control_area:
        stmt = stmt.where(CommercialControlPolicy.control_area == control_area)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_approval_chain(item) for item in items]


async def list_customer_evidence_packages(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(CommercialEvidencePackage)
        .where(CommercialEvidencePackage.client_id == client_id)
        .order_by(desc(CommercialEvidencePackage.created_at))
        .limit(limit)
    )
    for clause in _build_time_filters(
        CommercialEvidencePackage.created_at, period_start=period_start, period_end=period_end
    ):
        stmt = stmt.where(clause)
    if actor:
        stmt = stmt.where(CommercialEvidencePackage.summary.contains(actor))
    if control_area:
        stmt = stmt.where(CommercialEvidencePackage.package_type == control_area)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_evidence_package(item) for item in items]


async def list_customer_attestations(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(CommercialControlAttestation)
        .options(selectinload(CommercialControlAttestation.policy))
        .join(
            CommercialControlPolicy,
            CommercialControlAttestation.control_policy_id == CommercialControlPolicy.id,
        )
        .where(CommercialControlAttestation.client_id == client_id)
        .order_by(desc(CommercialControlAttestation.created_at))
        .limit(limit)
    )
    for clause in _build_date_overlap_filters(
        CommercialControlAttestation.attestation_period_start,
        CommercialControlAttestation.attestation_period_end,
        period_start=period_start,
        period_end=period_end,
    ):
        stmt = stmt.where(clause)
    if status:
        stmt = stmt.where(CommercialControlAttestation.status == status)
    if actor:
        stmt = stmt.where(CommercialControlAttestation.attested_by == actor)
    if control_area:
        stmt = stmt.where(CommercialControlPolicy.control_area == control_area)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_attestation(item) for item in items]


async def list_customer_exceptions(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    status: str | None = None,
    severity: str | None = None,
    control_area: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(CommercialControlException)
        .options(selectinload(CommercialControlException.policy))
        .join(
            CommercialControlPolicy,
            CommercialControlException.control_policy_id == CommercialControlPolicy.id,
            isouter=True,
        )
        .where(CommercialControlException.client_id == client_id)
        .order_by(desc(CommercialControlException.created_at))
        .limit(limit)
    )
    for clause in _build_time_filters(
        CommercialControlException.created_at, period_start=period_start, period_end=period_end
    ):
        stmt = stmt.where(clause)
    if status:
        stmt = stmt.where(CommercialControlException.status == status)
    if severity:
        stmt = stmt.where(CommercialControlException.severity == severity)
    if actor:
        stmt = stmt.where(CommercialControlException.owner == actor)
    if control_area:
        stmt = stmt.where(CommercialControlPolicy.control_area == control_area)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_exception(item) for item in items]


async def list_customer_saved_reports(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(CommercialPortalSavedReport)
        .where(CommercialPortalSavedReport.client_id == client_id)
        .order_by(desc(CommercialPortalSavedReport.created_at))
        .limit(limit)
    )
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_saved_report(item) for item in items]


async def list_customer_access_logs(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    actor: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(CommercialPortalAuditAccessLog)
        .where(CommercialPortalAuditAccessLog.client_id == client_id)
        .order_by(desc(CommercialPortalAuditAccessLog.created_at))
        .limit(limit)
    )
    for clause in _build_time_filters(
        CommercialPortalAuditAccessLog.created_at, period_start=period_start, period_end=period_end
    ):
        stmt = stmt.where(clause)
    if actor:
        stmt = stmt.where(CommercialPortalAuditAccessLog.actor_email == actor)
    if action:
        stmt = stmt.where(CommercialPortalAuditAccessLog.action == action)
    items = (await db.execute(stmt)).scalars().all()
    return [_serialize_access_log(item) for item in items]


async def _list_financial_events(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> dict[str, Any]:
    audit_start, audit_end = (
        _to_utc_datetime(period_start),
        _to_utc_datetime(period_end, end_of_day=True),
    )
    audit_stmt = (
        select(CommercialFinancialAuditEvent)
        .where(CommercialFinancialAuditEvent.client_id == client_id)
        .where(
            CommercialFinancialAuditEvent.created_at >= audit_start,
            CommercialFinancialAuditEvent.created_at <= audit_end,
        )
        .order_by(desc(CommercialFinancialAuditEvent.created_at))
        .limit(100)
    )
    recon_stmt = (
        select(CommercialFinancialReconciliation)
        .where(CommercialFinancialReconciliation.client_id == client_id)
        .where(
            CommercialFinancialReconciliation.created_at >= audit_start,
            CommercialFinancialReconciliation.created_at <= audit_end,
        )
        .order_by(desc(CommercialFinancialReconciliation.created_at))
        .limit(100)
    )
    dispute_stmt = (
        select(CommercialBillingDispute)
        .where(CommercialBillingDispute.client_id == client_id)
        .where(
            CommercialBillingDispute.created_at >= audit_start,
            CommercialBillingDispute.created_at <= audit_end,
        )
        .order_by(desc(CommercialBillingDispute.created_at))
        .limit(100)
    )
    qos_stmt = (
        select(CommercialQoSBillingRecord)
        .where(CommercialQoSBillingRecord.client_id == client_id)
        .where(
            CommercialQoSBillingRecord.created_at >= audit_start,
            CommercialQoSBillingRecord.created_at <= audit_end,
        )
        .order_by(desc(CommercialQoSBillingRecord.created_at))
        .limit(100)
    )
    invoice_stmt = (
        select(BillingInvoice)
        .where(BillingInvoice.client_id == client_id)
        .where(BillingInvoice.period_end >= period_start, BillingInvoice.period_start <= period_end)
        .order_by(desc(BillingInvoice.created_at))
        .limit(100)
    )
    audits = (await db.execute(audit_stmt)).scalars().all()
    reconciliations = (await db.execute(recon_stmt)).scalars().all()
    disputes = (await db.execute(dispute_stmt)).scalars().all()
    qos_records = (await db.execute(qos_stmt)).scalars().all()
    invoices = (await db.execute(invoice_stmt)).scalars().all()
    return sanitize_report_payload(
        {
            "financial_audit_events": [
                {
                    "id": str(item.id),
                    "event_type": item.event_type,
                    "related_record_type": item.related_record_type,
                    "related_record_id": item.related_record_id,
                    "amount_brl": float(item.amount_brl) if item.amount_brl is not None else None,
                    "metadata_json": item.metadata_json or {},
                    "immutable_hash": item.immutable_hash,
                    "created_at": item.created_at.isoformat(),
                }
                for item in audits
            ],
            "reconciliations": [
                {
                    "id": str(item.id),
                    "reconciliation_type": item.reconciliation_type,
                    "status": item.status,
                    "expected_amount_brl": float(item.expected_amount_brl),
                    "actual_amount_brl": float(item.actual_amount_brl),
                    "delta_amount_brl": float(item.delta_amount_brl),
                    "discrepancy_percent": float(item.discrepancy_percent),
                    "created_at": item.created_at.isoformat(),
                }
                for item in reconciliations
            ],
            "disputes": [
                {
                    "id": str(item.id),
                    "dispute_type": item.dispute_type,
                    "status": item.status,
                    "claimed_amount_brl": float(item.claimed_amount_brl),
                    "created_at": item.created_at.isoformat(),
                }
                for item in disputes
            ],
            "qos_billing": [
                {
                    "id": str(item.id),
                    "qos_tier": item.qos_tier,
                    "status": item.status,
                    "billable_amount_brl": float(item.billable_amount_brl),
                    "period_start": item.period_start.isoformat(),
                    "period_end": item.period_end.isoformat(),
                }
                for item in qos_records
            ],
            "invoices": [
                {
                    "id": str(item.id),
                    "status": item.status,
                    "total_amount": float(item.total_amount),
                    "currency": item.currency,
                    "period_start": item.period_start.isoformat(),
                    "period_end": item.period_end.isoformat(),
                }
                for item in invoices
            ],
        }
    )


def _report_payload_by_type(
    *,
    report_type: str,
    approval_chains: list[dict[str, Any]],
    evidence_packages: list[dict[str, Any]],
    attestations: list[dict[str, Any]],
    exceptions: list[dict[str, Any]],
    financial_events: dict[str, Any],
    operational_controls: list[dict[str, Any]],
    operational_evidence: list[dict[str, Any]],
    operational_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "approval_chains": approval_chains,
        "evidence_packages": evidence_packages,
        "attestations": attestations,
        "exceptions": exceptions,
        "financial_events": financial_events,
        "operational_controls": operational_controls,
        "operational_evidence": operational_evidence,
        "operational_reviews": operational_reviews,
    }
    if report_type == "approval_chain":
        return {"approval_chains": approval_chains}
    if report_type == "evidence":
        return {"evidence_packages": evidence_packages}
    if report_type == "attestation":
        return {"attestations": attestations}
    if report_type == "exception":
        return {"exceptions": exceptions}
    if report_type == "financial_summary":
        return {"financial_events": financial_events}
    return payload


def _flatten_report_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"section": "watermark", "id": "", "status": "", "summary": EXPORT_WATERMARK}
    ]
    for section_name, items in payload.items():
        if isinstance(items, dict):
            for child_name, child_items in items.items():
                if isinstance(child_items, list):
                    for item in child_items:
                        rows.append(
                            {
                                "section": f"{section_name}.{child_name}",
                                "id": item.get("id", ""),
                                "status": item.get("status", ""),
                                "summary": json.dumps(
                                    sanitize_report_payload(item),
                                    ensure_ascii=True,
                                    sort_keys=True,
                                    default=str,
                                ),
                            }
                        )
        elif isinstance(items, list):
            for item in items:
                rows.append(
                    {
                        "section": section_name,
                        "id": item.get("id", ""),
                        "status": item.get("status", ""),
                        "summary": json.dumps(
                            sanitize_report_payload(item),
                            ensure_ascii=True,
                            sort_keys=True,
                            default=str,
                        ),
                    }
                )
    return rows


def export_customer_report(report: dict[str, Any], export_format: str) -> bytes:
    sanitized = sanitize_report_payload(report)
    if export_format == "json":
        payload = {
            "export_watermark": EXPORT_WATERMARK,
            **(sanitized if isinstance(sanitized, dict) else {"report": sanitized}),
        }
        return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True, default=str).encode(
            "utf-8"
        )

    if export_format == "csv":
        rows = _flatten_report_rows(
            sanitized if isinstance(sanitized, dict) else {"report": sanitized}
        )
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["section", "id", "status", "summary"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")

    if export_format in {"html", "pdf"}:
        body = sanitized if isinstance(sanitized, dict) else {"report": sanitized}
        html_sections = []
        for section_name, section_value in body.items():
            html_sections.append(
                f"<section><h2>{html.escape(str(section_name))}</h2><pre>{html.escape(json.dumps(section_value, ensure_ascii=True, indent=2, sort_keys=True, default=str))}</pre></section>"
            )
        html_doc = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Enterprise Audit Export</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; color: #111827; }}
      .watermark {{ font-size: 14px; font-weight: 700; color: #991b1b; border: 2px solid #fecaca; padding: 12px; margin-bottom: 24px; }}
      pre {{ background: #f8fafc; border: 1px solid #e5e7eb; padding: 16px; overflow-x: auto; white-space: pre-wrap; }}
      section {{ margin-bottom: 24px; }}
    </style>
  </head>
  <body>
    <div class="watermark">{html.escape(EXPORT_WATERMARK)}</div>
    {"".join(html_sections)}
  </body>
</html>"""
        if export_format == "html":
            return html_doc.encode("utf-8")
        settings = get_settings()
        if not settings.commercial_enterprise_audit_export_pdf_enabled:
            raise HTTPException(status_code=501, detail="pdf export disabled")
        try:
            from weasyprint import HTML
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise HTTPException(status_code=501, detail="pdf export unavailable") from exc
        return HTML(string=html_doc).write_pdf()

    raise HTTPException(status_code=400, detail="unsupported export format")


async def generate_customer_audit_report(
    db: AsyncSession,
    *,
    client: Client,
    client_id: uuid.UUID,
    report_type: str,
    period_start: date,
    period_end: date,
    filters_json: dict[str, Any] | None,
    export_format: str,
    actor_id: str | None = None,
    actor_email: str | None = None,
    actor_name: str | None = None,
) -> tuple[CommercialPortalSavedReport, dict[str, Any]]:
    filters = _sanitize_json(filters_json or {})
    approval_chains = await list_customer_approval_chains(
        db,
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        status=filters.get("status"),
        control_area=filters.get("control_area"),
        actor=filters.get("actor"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    evidence_packages = await list_customer_evidence_packages(
        db,
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        control_area=filters.get("control_area"),
        actor=filters.get("actor"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    attestations = await list_customer_attestations(
        db,
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        status=filters.get("status"),
        control_area=filters.get("control_area"),
        actor=filters.get("actor"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    exceptions = await list_customer_exceptions(
        db,
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
        status=filters.get("status"),
        severity=filters.get("severity"),
        control_area=filters.get("control_area"),
        actor=filters.get("actor"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    financial_events = await _list_financial_events(
        db,
        client_id=client_id,
        period_start=period_start,
        period_end=period_end,
    )
    operational_controls = await list_customer_operational_controls(
        db,
        client_id=client_id,
        control_category=filters.get("control_category"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    operational_evidence = await list_customer_operational_evidence(
        db,
        client_id=client_id,
        freshness_status=filters.get("freshness_status"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    operational_reviews = await list_customer_operational_reviews(
        db,
        client_id=client_id,
        status=filters.get("review_status"),
        limit=min(int(filters.get("limit", 250)), 500),
    )
    payload = sanitize_report_payload(
        {
            "export_watermark": EXPORT_WATERMARK,
            "generated_at": utc_now().isoformat(),
            "client_id": str(client_id),
            "report_type": report_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "filters_json": filters,
            "summary": {
                "approval_chains": len(approval_chains),
                "evidence_packages": len(evidence_packages),
                "attestations": len(attestations),
                "exceptions": len(exceptions),
                "financial_audit_events": len(financial_events.get("financial_audit_events", [])),
                "reconciliations": len(financial_events.get("reconciliations", [])),
                "disputes": len(financial_events.get("disputes", [])),
                "qos_billing_records": len(financial_events.get("qos_billing", [])),
                "invoices": len(financial_events.get("invoices", [])),
                "operational_controls": len(operational_controls),
                "operational_evidence": len(operational_evidence),
                "operational_reviews": len(operational_reviews),
            },
            "data": _report_payload_by_type(
                report_type=report_type,
                approval_chains=approval_chains,
                evidence_packages=evidence_packages,
                attestations=attestations,
                exceptions=exceptions,
                financial_events=financial_events,
                operational_controls=operational_controls,
                operational_evidence=operational_evidence,
                operational_reviews=operational_reviews,
            ),
        }
    )
    immutable_hash = _hash_payload(payload)
    actor = _infer_actor(client, actor_id=actor_id, actor_email=actor_email, actor_name=actor_name)
    report = CommercialPortalSavedReport(
        client_id=client_id,
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        filters_json=filters,
        export_format=export_format,
        generated_by=actor.actor_email
        or actor.actor_name
        or (str(actor.actor_id) if actor.actor_id else None),
        immutable_hash=immutable_hash,
        created_at=utc_now(),
        expires_at=utc_now()
        + timedelta(days=get_settings().commercial_enterprise_audit_log_retention_days),
    )
    db.add(report)
    await db.flush()

    extension = "pdf" if export_format == "pdf" else export_format
    report_dir = _exports_root() / str(client_id)
    report_dir.mkdir(parents=True, exist_ok=True)
    storage_path = report_dir / f"{report.id}.{extension}"
    content = export_customer_report(payload, export_format)
    storage_path.write_bytes(content)
    report.storage_ref = str(storage_path)
    await db.flush()
    return report, payload


async def log_portal_access(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    actor_id: str | None = None,
    actor_email: str | None = None,
    resource_type: str,
    resource_id: str | None = None,
    action: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> CommercialPortalAuditAccessLog:
    parsed_actor_id: uuid.UUID | None = None
    if actor_id:
        try:
            parsed_actor_id = uuid.UUID(str(actor_id))
        except ValueError:
            parsed_actor_id = None

    item = CommercialPortalAuditAccessLog(
        client_id=client_id,
        actor_id=parsed_actor_id,
        actor_email=_sanitize_email(actor_email),
        resource_type=_sanitize_text(resource_type, limit=64) or "unknown",
        resource_id=_sanitize_text(resource_id, limit=128),
        action=_sanitize_text(action, limit=16) or "view",
        ip_masked=_mask_ip(ip_address),
        user_agent_sanitized=_sanitize_text(user_agent, limit=UA_LIMIT),
        metadata_json=_sanitize_json(metadata_json or {}),
        created_at=utc_now(),
    )
    db.add(item)
    await db.flush()
    return item
