from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_compliance import (
    CommercialControlAttestation,
    CommercialControlException,
    CommercialOperationalControl,
    CommercialOperationalEvidence,
    CommercialOperationalExceptionLink,
    CommercialOperationalReview,
)
from app.models.commercial.commercial_financial_reconciliation import (
    CommercialFinancialReconciliation,
)
from app.services.compliance.financial_controls import create_evidence_package, record_control_event
from app.services.notifications.revenue_escalations import evaluate_escalation_policies
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

SECRET_KEYS = {
    "api_key",
    "api_keys",
    "authorization",
    "prompt",
    "prompts",
    "response",
    "responses",
    "secret",
    "secrets",
    "token",
    "tokens",
    "smtp_password",
    "webhook_secret",
}
VALID_CATEGORIES = {
    "security",
    "availability",
    "processing_integrity",
    "confidentiality",
    "privacy",
    "financial",
    "operational",
}
VALID_REVIEW_FREQUENCIES = {"monthly", "quarterly", "semiannual", "annual"}
VALID_EFFECTIVENESS_STATUSES = {"effective", "partially_effective", "ineffective", "unknown"}
VALID_EVIDENCE_TYPES = {
    "screenshot",
    "report",
    "export",
    "audit_log",
    "approval_chain",
    "attestation",
    "reconciliation",
    "other",
}
VALID_REVIEW_STATUSES = {"pending", "completed", "overdue", "exception"}
VALID_EXCEPTION_REMEDIATION_STATUSES = {"planned", "in_progress", "completed"}
VALID_FRESHNESS_STATUSES = {"fresh", "stale", "expired"}


def _sanitize_text(value: str | None, limit: int = 4000) -> str | None:
    if value is None:
        return None
    return value.replace("\r", " ").replace("\n", " ").strip()[:limit]


def _sanitize_node(node: Any) -> Any:
    if isinstance(node, dict):
        cleaned: dict[str, Any] = {}
        for key, value in node.items():
            lowered = str(key).lower()
            if lowered in SECRET_KEYS:
                continue
            cleaned[str(key)] = _sanitize_node(value)
        return sanitize_report_payload(cleaned)
    if isinstance(node, list):
        return [_sanitize_node(item) for item in node]
    return sanitize_report_payload(node)


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(
        sanitize_report_payload(payload), sort_keys=True, ensure_ascii=True, default=str
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _period_delta(frequency: str) -> timedelta:
    mapping = {
        "monthly": timedelta(days=30),
        "quarterly": timedelta(days=90),
        "semiannual": timedelta(days=182),
        "annual": timedelta(days=365),
    }
    return mapping.get(frequency, timedelta(days=90))


def _review_window(frequency: str, *, anchor: date | None = None) -> tuple[date, date]:
    start = anchor or utc_now().date()
    end = start + _period_delta(frequency)
    return start, end


def _date_to_dt(value: date, *, end_of_day: bool = False) -> datetime:
    clock = time.max if end_of_day else time.min
    return datetime.combine(value, clock, tzinfo=UTC)


def _status_from_score(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score >= 90:
        return "effective"
    if score >= 50:
        return "partially_effective"
    return "ineffective"


def refresh_evidence_status(
    evidence: CommercialOperationalEvidence,
    *,
    control: CommercialOperationalControl | None = None,
    as_of: datetime | None = None,
) -> str:
    reference = as_of or utc_now()
    if evidence.expires_at and evidence.expires_at <= reference:
        evidence.freshness_status = "expired"
        return evidence.freshness_status
    sla_days = max(
        1,
        int(
            (control.evidence_sla_days if control else None)
            or get_settings().commercial_operational_control_default_evidence_sla_days
        ),
    )
    age_days = max(0, (reference - evidence.collected_at).days)
    if age_days >= sla_days:
        evidence.freshness_status = "expired"
    elif age_days >= max(1, int(sla_days * 0.8)):
        evidence.freshness_status = "stale"
    else:
        evidence.freshness_status = "fresh"
    return evidence.freshness_status


async def create_control(
    db: AsyncSession,
    *,
    control_code: str,
    name: str,
    category: str,
    description: str | None = None,
    owner_id: uuid.UUID | None = None,
    owner_email: str | None = None,
    review_frequency: str = "quarterly",
    evidence_sla_days: int | None = None,
    enabled: bool = True,
    metadata_json: dict[str, Any] | None = None,
) -> CommercialOperationalControl:
    if category not in VALID_CATEGORIES:
        raise ValueError("invalid_control_category")
    if review_frequency not in VALID_REVIEW_FREQUENCIES:
        raise ValueError("invalid_review_frequency")
    start, end = _review_window(review_frequency)
    item = CommercialOperationalControl(
        control_code=_sanitize_text(control_code, 64) or "",
        name=_sanitize_text(name, 255) or "",
        category=category,
        description=_sanitize_text(description),
        owner_id=owner_id,
        owner_email=_sanitize_text(owner_email, 255),
        review_frequency=review_frequency,
        effectiveness_status="unknown",
        effectiveness_score=None,
        evidence_sla_days=max(
            1,
            int(
                evidence_sla_days
                or get_settings().commercial_operational_control_default_evidence_sla_days
            ),
        ),
        next_review_due_at=_date_to_dt(end, end_of_day=True),
        enabled=enabled,
        metadata_json=_sanitize_node(metadata_json or {}),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(item)
    await db.flush()
    await generate_pending_review(db, control_id=item.id, anchor=start)
    await record_control_event(
        db,
        action="operational_control_created",
        status="created",
        payload={"control_code": item.control_code, "category": item.category},
        result={"control_id": str(item.id)},
    )
    return item


async def update_control(
    db: AsyncSession, control_id: uuid.UUID, **updates: Any
) -> CommercialOperationalControl:
    item = await db.get(CommercialOperationalControl, control_id)
    if item is None:
        raise ValueError("operational_control_not_found")
    allowed = {
        "control_code",
        "name",
        "category",
        "description",
        "owner_id",
        "owner_email",
        "review_frequency",
        "evidence_sla_days",
        "enabled",
        "metadata_json",
        "effectiveness_status",
        "effectiveness_score",
        "last_reviewed_at",
        "next_review_due_at",
    }
    for key, value in updates.items():
        if key not in allowed or value is None:
            continue
        if key == "category" and value not in VALID_CATEGORIES:
            raise ValueError("invalid_control_category")
        if key == "review_frequency" and value not in VALID_REVIEW_FREQUENCIES:
            raise ValueError("invalid_review_frequency")
        if key == "effectiveness_status" and value not in VALID_EFFECTIVENESS_STATUSES:
            raise ValueError("invalid_effectiveness_status")
        if key == "metadata_json":
            value = _sanitize_node(value)
        elif key in {"control_code", "name", "owner_email"}:
            value = _sanitize_text(str(value), 255)
        elif key == "description":
            value = _sanitize_text(value)
        setattr(item, key, value)
    item.updated_at = utc_now()
    await db.flush()
    await record_control_event(
        db,
        action="operational_control_updated",
        status="updated",
        payload={
            "control_id": str(item.id),
            "fields": sorted(key for key in updates if key in allowed),
        },
        result={"control_code": item.control_code},
    )
    return item


async def add_operational_evidence(
    db: AsyncSession,
    *,
    control_id: uuid.UUID,
    evidence_type: str,
    title: str,
    summary: str | None = None,
    evidence_json: dict[str, Any] | None = None,
    collected_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> CommercialOperationalEvidence:
    if evidence_type not in VALID_EVIDENCE_TYPES:
        raise ValueError("invalid_evidence_type")
    control = await db.get(CommercialOperationalControl, control_id)
    if control is None:
        raise ValueError("operational_control_not_found")
    collected = collected_at or utc_now()
    payload = {
        "control_id": str(control_id),
        "evidence_type": evidence_type,
        "title": title,
        "summary": summary,
        "collected_at": collected.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "evidence_json": _sanitize_node(evidence_json or {}),
    }
    item = CommercialOperationalEvidence(
        control_id=control_id,
        evidence_type=evidence_type,
        title=_sanitize_text(title, 255) or "",
        summary=_sanitize_text(summary),
        evidence_json=_sanitize_node(evidence_json or {}),
        immutable_hash=_hash_payload(payload),
        freshness_status="fresh",
        collected_at=collected,
        expires_at=expires_at,
        created_at=utc_now(),
    )
    refresh_evidence_status(item, control=control)
    db.add(item)
    await db.flush()
    await record_control_event(
        db,
        action="operational_evidence_created",
        status=item.freshness_status,
        payload={"control_id": str(control_id), "evidence_type": evidence_type},
        result={"evidence_id": str(item.id), "immutable_hash": item.immutable_hash},
    )
    return item


async def generate_pending_review(
    db: AsyncSession,
    *,
    control_id: uuid.UUID,
    anchor: date | None = None,
) -> CommercialOperationalReview:
    control = await db.get(CommercialOperationalControl, control_id)
    if control is None:
        raise ValueError("operational_control_not_found")
    start, end = _review_window(control.review_frequency, anchor=anchor)
    existing_stmt = select(CommercialOperationalReview).where(
        CommercialOperationalReview.control_id == control_id,
        CommercialOperationalReview.review_period_start == start,
        CommercialOperationalReview.review_period_end == end,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        return existing
    review = CommercialOperationalReview(
        control_id=control_id,
        review_period_start=start,
        review_period_end=end,
        status="pending",
        created_at=utc_now(),
    )
    db.add(review)
    control.next_review_due_at = _date_to_dt(end, end_of_day=True)
    control.updated_at = utc_now()
    await db.flush()
    return review


async def assign_review_reviewer(
    db: AsyncSession,
    *,
    review_id: uuid.UUID,
    reviewed_by: str,
) -> CommercialOperationalReview:
    review = await db.get(CommercialOperationalReview, review_id)
    if review is None:
        raise ValueError("operational_review_not_found")
    review.reviewed_by = _sanitize_text(reviewed_by, 255)
    await db.flush()
    return review


async def complete_review(
    db: AsyncSession,
    *,
    review_id: uuid.UUID,
    reviewed_by: str | None = None,
    findings: str | None = None,
    recommendations: str | None = None,
    evidence_package_id: uuid.UUID | None = None,
    create_policy_attestation: bool = False,
) -> CommercialOperationalReview:
    review = await db.get(CommercialOperationalReview, review_id)
    if review is None:
        raise ValueError("operational_review_not_found")
    review.reviewed_by = _sanitize_text(reviewed_by or review.reviewed_by, 255)
    review.findings = _sanitize_text(findings)
    review.recommendations = _sanitize_text(recommendations)
    review.evidence_package_id = evidence_package_id
    review.status = "completed"
    review.completed_at = utc_now()

    control = await db.get(CommercialOperationalControl, review.control_id)
    if control is not None:
        control.last_reviewed_at = review.completed_at
        _, next_end = _review_window(
            control.review_frequency, anchor=review.review_period_end + timedelta(days=1)
        )
        control.next_review_due_at = _date_to_dt(next_end, end_of_day=True)
        control.updated_at = utc_now()
        await generate_pending_review(
            db, control_id=control.id, anchor=review.review_period_end + timedelta(days=1)
        )
        await evaluate_control_effectiveness(db, control.id)

    if create_policy_attestation and control is not None:
        await create_evidence_package(
            db,
            package_type="operational_review",
            target_type="CommercialOperationalReview",
            target_id=review.id,
            summary=f"Operational review completed for {control.control_code}",
            actor=review.reviewed_by or "system",
            payload={
                "findings": review.findings,
                "recommendations": review.recommendations,
                "evidence_package_id": str(evidence_package_id) if evidence_package_id else None,
            },
        )
    await record_control_event(
        db,
        action="operational_review_completed",
        status=review.status,
        payload={"review_id": str(review.id), "reviewed_by": review.reviewed_by},
        result={"control_id": str(review.control_id)},
    )
    return review


async def link_exception(
    db: AsyncSession,
    *,
    control_id: uuid.UUID,
    exception_id: uuid.UUID,
    linkage_reason: str | None = None,
    remediation_status: str = "planned",
) -> CommercialOperationalExceptionLink:
    if remediation_status not in VALID_EXCEPTION_REMEDIATION_STATUSES:
        raise ValueError("invalid_remediation_status")
    existing_stmt = select(CommercialOperationalExceptionLink).where(
        CommercialOperationalExceptionLink.control_id == control_id,
        CommercialOperationalExceptionLink.exception_id == exception_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        return existing
    item = CommercialOperationalExceptionLink(
        control_id=control_id,
        exception_id=exception_id,
        linkage_reason=_sanitize_text(linkage_reason),
        remediation_status=remediation_status,
        created_at=utc_now(),
    )
    db.add(item)
    await db.flush()
    await record_control_event(
        db,
        action="operational_exception_link_created",
        status=remediation_status,
        payload={"control_id": str(control_id), "exception_id": str(exception_id)},
        result={"link_id": str(item.id)},
    )
    return item


async def detect_stale_evidence(
    db: AsyncSession,
    *,
    control_id: uuid.UUID | None = None,
    as_of: datetime | None = None,
) -> list[CommercialOperationalEvidence]:
    stmt = select(CommercialOperationalEvidence).order_by(
        desc(CommercialOperationalEvidence.created_at)
    )
    if control_id is not None:
        stmt = stmt.where(CommercialOperationalEvidence.control_id == control_id)
    evidences = list((await db.execute(stmt)).scalars().all())
    controls = {
        item.id: item
        for item in (await db.execute(select(CommercialOperationalControl))).scalars().all()
    }
    for evidence in evidences:
        refresh_evidence_status(evidence, control=controls.get(evidence.control_id), as_of=as_of)
    await db.flush()
    return [item for item in evidences if item.freshness_status in {"stale", "expired"}]


async def detect_overdue_reviews(
    db: AsyncSession,
    *,
    control_id: uuid.UUID | None = None,
    as_of: datetime | None = None,
) -> list[CommercialOperationalReview]:
    reference = (as_of or utc_now()).date()
    stmt = select(CommercialOperationalReview).order_by(
        desc(CommercialOperationalReview.review_period_end)
    )
    if control_id is not None:
        stmt = stmt.where(CommercialOperationalReview.control_id == control_id)
    reviews = list((await db.execute(stmt)).scalars().all())
    for review in reviews:
        if review.status == "pending" and review.review_period_end < reference:
            review.status = "overdue"
    await db.flush()
    return [item for item in reviews if item.status == "overdue"]


async def calculate_effectiveness_score(db: AsyncSession, control_id: uuid.UUID) -> int:
    control = await db.get(CommercialOperationalControl, control_id)
    if control is None:
        raise ValueError("operational_control_not_found")
    score = 100

    stale = await detect_stale_evidence(db, control_id=control_id)
    expired_count = sum(1 for item in stale if item.freshness_status == "expired")
    stale_count = sum(1 for item in stale if item.freshness_status == "stale")
    score -= expired_count * 35
    score -= stale_count * 15

    overdue_reviews = await detect_overdue_reviews(db, control_id=control_id)
    score -= len(overdue_reviews) * 20

    link_stmt = (
        select(CommercialOperationalExceptionLink, CommercialControlException)
        .join(
            CommercialControlException,
            CommercialOperationalExceptionLink.exception_id == CommercialControlException.id,
        )
        .where(CommercialOperationalExceptionLink.control_id == control_id)
    )
    links = (await db.execute(link_stmt)).all()
    open_exceptions = 0
    repeated_exceptions = 0
    for link, exception in links:
        if exception.status in {"open", "accepted"} or link.remediation_status != "completed":
            open_exceptions += 1
    if open_exceptions >= 2:
        repeated_exceptions = open_exceptions
    score -= open_exceptions * 15
    score -= repeated_exceptions * 5

    failed_attestations = (
        await db.execute(
            select(func.count(CommercialControlAttestation.id)).where(
                CommercialControlAttestation.status.in_(["failed", "exception"])
            )
        )
    ).scalar() or 0
    score -= min(int(failed_attestations), 3) * 5

    unresolved_mismatches = (
        await db.execute(
            select(func.count(CommercialFinancialReconciliation.id)).where(
                CommercialFinancialReconciliation.status.in_(
                    ["mismatch", "investigating", "warning"]
                )
            )
        )
    ).scalar() or 0
    score -= min(int(unresolved_mismatches), 4) * 5
    return max(0, min(100, int(score)))


async def evaluate_control_effectiveness(
    db: AsyncSession, control_id: uuid.UUID
) -> CommercialOperationalControl:
    control = await db.get(CommercialOperationalControl, control_id)
    if control is None:
        raise ValueError("operational_control_not_found")
    score = await calculate_effectiveness_score(db, control_id)
    control.effectiveness_score = score
    control.effectiveness_status = _status_from_score(score)
    control.updated_at = utc_now()
    await db.flush()
    return control


async def _collect_control_status(
    db: AsyncSession,
    control: CommercialOperationalControl,
) -> dict[str, Any]:
    evidences = (
        (
            await db.execute(
                select(CommercialOperationalEvidence)
                .where(CommercialOperationalEvidence.control_id == control.id)
                .order_by(desc(CommercialOperationalEvidence.collected_at))
            )
        )
        .scalars()
        .all()
    )
    for evidence in evidences:
        refresh_evidence_status(evidence, control=control)

    reviews = (
        (
            await db.execute(
                select(CommercialOperationalReview)
                .where(CommercialOperationalReview.control_id == control.id)
                .order_by(desc(CommercialOperationalReview.review_period_end))
            )
        )
        .scalars()
        .all()
    )
    overdue_reviews = [
        review
        for review in reviews
        if review.status == "overdue"
        or (review.status == "pending" and review.review_period_end < utc_now().date())
    ]
    for review in overdue_reviews:
        if review.status == "pending":
            review.status = "overdue"

    link_rows = (
        await db.execute(
            select(CommercialOperationalExceptionLink, CommercialControlException)
            .join(
                CommercialControlException,
                CommercialOperationalExceptionLink.exception_id == CommercialControlException.id,
            )
            .where(CommercialOperationalExceptionLink.control_id == control.id)
        )
    ).all()
    linked_exceptions = [
        {
            "link_id": str(link.id),
            "exception_id": str(exception.id),
            "status": exception.status,
            "severity": exception.severity,
            "owner": _sanitize_text(exception.owner, 255),
            "remediation_status": link.remediation_status,
            "description": _sanitize_text(exception.description, 500),
            "linkage_reason": _sanitize_text(link.linkage_reason, 500),
            "client_id": str(exception.client_id) if exception.client_id else None,
        }
        for link, exception in link_rows
    ]
    return {
        "control": control,
        "evidences": evidences,
        "reviews": reviews,
        "overdue_reviews": overdue_reviews,
        "linked_exceptions": linked_exceptions,
    }


async def escalate_overdue_items(db: AsyncSession) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.commercial_operational_control_overdue_escalations_enabled:
        return []
    if not settings.commercial_operational_controls_enabled:
        return []
    results: list[dict[str, Any]] = []
    controls = (
        (
            await db.execute(
                select(CommercialOperationalControl).where(
                    CommercialOperationalControl.enabled.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )
    for control in controls:
        control = await evaluate_control_effectiveness(db, control.id)
        status = await _collect_control_status(db, control)
        trigger: str | None = None
        severity = "medium"
        summary = f"Operational control {control.control_code} requires attention"
        if any(item.freshness_status == "expired" for item in status["evidences"]):
            trigger = "stale_evidence"
            severity = "high"
            summary = f"Operational control {control.control_code} has expired evidence"
        elif status["overdue_reviews"]:
            trigger = "overdue_review"
            severity = "high"
            summary = f"Operational control {control.control_code} has overdue reviews"
        elif control.effectiveness_status == "ineffective":
            trigger = "ineffective_control"
            severity = "critical"
            summary = f"Operational control {control.control_code} is ineffective"
        elif (
            sum(1 for item in status["linked_exceptions"] if item["status"] in {"open", "accepted"})
            >= 2
        ):
            trigger = "repeated_exceptions"
            severity = "high"
            summary = f"Operational control {control.control_code} has repeated linked exceptions"
        if not trigger:
            continue
        delivery_types = ["webhook", "email"]
        outcome = await evaluate_escalation_policies(
            db,
            source_type="policy_action",
            source_id=control.id,
            severity=severity,
            summary=summary,
            recommendation="Review the operational control owner, evidence freshness, and remediation plan.",
            trigger_type=trigger,
            metadata={
                "control_id": str(control.id),
                "control_code": control.control_code,
                "effectiveness_score": control.effectiveness_score,
                "effectiveness_status": control.effectiveness_status,
            },
            delivery_types=delivery_types,
        )
        await record_control_event(
            db,
            action="operational_control_escalated",
            status=trigger,
            payload={"control_id": str(control.id), "trigger_type": trigger},
            result={"deliveries": outcome.get("deliveries", []), "mode": outcome.get("mode")},
        )
        results.append(
            {
                "control_id": str(control.id),
                "control_code": control.control_code,
                "trigger_type": trigger,
                "severity": severity,
                "delivery_result": outcome,
                "internal_escalation": True,
            }
        )
    await db.flush()
    return results


async def summarize_operational_controls(db: AsyncSession) -> dict[str, Any]:
    controls = (
        (
            await db.execute(
                select(CommercialOperationalControl).order_by(
                    CommercialOperationalControl.control_code.asc()
                )
            )
        )
        .scalars()
        .all()
    )
    stale_evidence = await detect_stale_evidence(db)
    overdue_reviews = await detect_overdue_reviews(db)
    ineffective_controls = 0
    items: list[dict[str, Any]] = []
    review_calendar: list[dict[str, Any]] = []
    for control in controls:
        control = await evaluate_control_effectiveness(db, control.id)
        if control.effectiveness_status == "ineffective":
            ineffective_controls += 1
        status = await _collect_control_status(db, control)
        items.append(
            {
                "id": str(control.id),
                "control_code": control.control_code,
                "name": control.name,
                "category": control.category,
                "owner_email": control.owner_email,
                "review_frequency": control.review_frequency,
                "effectiveness_score": control.effectiveness_score,
                "effectiveness_status": control.effectiveness_status,
                "evidence_sla_days": control.evidence_sla_days,
                "last_reviewed_at": control.last_reviewed_at.isoformat()
                if control.last_reviewed_at
                else None,
                "next_review_due_at": control.next_review_due_at.isoformat()
                if control.next_review_due_at
                else None,
                "enabled": control.enabled,
                "linked_exceptions": status["linked_exceptions"],
                "freshness_counts": {
                    "fresh": sum(
                        1 for item in status["evidences"] if item.freshness_status == "fresh"
                    ),
                    "stale": sum(
                        1 for item in status["evidences"] if item.freshness_status == "stale"
                    ),
                    "expired": sum(
                        1 for item in status["evidences"] if item.freshness_status == "expired"
                    ),
                },
                "overdue_reviews": len(status["overdue_reviews"]),
                "badges": [
                    "EFFECTIVE" if control.effectiveness_status == "effective" else None,
                    "PARTIAL" if control.effectiveness_status == "partially_effective" else None,
                    "INEFFECTIVE" if control.effectiveness_status == "ineffective" else None,
                    "STALE"
                    if any(
                        item.freshness_status in {"stale", "expired"}
                        for item in status["evidences"]
                    )
                    else None,
                    "OVERDUE" if status["overdue_reviews"] else None,
                    "EXCEPTION_LINKED" if status["linked_exceptions"] else None,
                ],
            }
        )
        review_calendar.extend(
            {
                "review_id": str(review.id),
                "control_id": str(control.id),
                "control_code": control.control_code,
                "status": review.status,
                "review_period_start": review.review_period_start.isoformat(),
                "review_period_end": review.review_period_end.isoformat(),
                "reviewed_by": review.reviewed_by,
                "completed_at": review.completed_at.isoformat() if review.completed_at else None,
            }
            for review in status["reviews"][:4]
        )
    escalation_status = await escalate_overdue_items(db)
    return sanitize_report_payload(
        {
            "summary": {
                "controls": len(controls),
                "stale_evidence": len(stale_evidence),
                "overdue_reviews": len(overdue_reviews),
                "ineffective_controls": ineffective_controls,
                "linked_exceptions": sum(1 for item in items if item["linked_exceptions"]),
            },
            "controls": items,
            "review_calendar": review_calendar,
            "escalation_status": escalation_status,
        }
    )


__all__ = [
    "add_operational_evidence",
    "assign_review_reviewer",
    "calculate_effectiveness_score",
    "complete_review",
    "create_control",
    "detect_overdue_reviews",
    "detect_stale_evidence",
    "escalate_overdue_items",
    "evaluate_control_effectiveness",
    "generate_pending_review",
    "link_exception",
    "refresh_evidence_status",
    "summarize_operational_controls",
    "update_control",
]
