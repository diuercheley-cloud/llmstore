from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_compliance import (
    CommercialApprovalChain,
    CommercialControlAttestation,
    CommercialControlException,
    CommercialControlPolicy,
    CommercialEvidencePackage,
)
from app.models.core.admin_action_log import AdminActionLog
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.tenant_encryption import TenantEncryptionService
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

_settings = get_settings()
_encryption_service = TenantEncryptionService(_settings)

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
    "smtp_password",
    "provider_secret",
    "provider_secrets",
    "token",
    "tokens",
    "payload",
    "raw_payload",
}


class ControlViolationError(ValueError):
    pass


@dataclass
class ControlDecision:
    enabled: bool
    mode: str
    policy: CommercialControlPolicy | None
    requires_approval: bool
    segregation_required: bool
    evidence_required: bool
    required_approver_count: int
    should_block: bool
    pending_approval: bool
    approval_chain: CommercialApprovalChain | None = None
    evidence_package: CommercialEvidencePackage | None = None


def _sanitize_text(value: str | None, limit: int = 2000) -> str | None:
    if value is None:
        return None
    return value.replace("\r", " ").replace("\n", " ")[:limit]


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


def _frequency_window_end(start: date, frequency: str) -> date:
    if frequency == "monthly":
        return start + timedelta(days=30)
    if frequency == "annual":
        return start + timedelta(days=365)
    return start + timedelta(days=90)


async def create_evidence_package(
    db: AsyncSession,
    *,
    client_id: uuid.UUID | None = None,
    package_type: str,
    target_type: str,
    target_id: str | uuid.UUID,
    summary: str,
    actor: str,
    before_state: Any = None,
    after_state: Any = None,
    payload: Any = None,
    related_ids: dict[str, Any] | None = None,
    file_refs: dict[str, Any] | list[Any] | None = None,
    timestamp: datetime | None = None,
) -> CommercialEvidencePackage:
    created_at = timestamp or utc_now()
    evidence_json = {
        "before_state": _sanitize_node(before_state or {}),
        "after_state": _sanitize_node(after_state or {}),
        "actor": actor,
        "timestamp": created_at.isoformat(),
        "related_ids": _sanitize_node(related_ids or {}),
        "payload": _sanitize_node(payload or {}),
    }
    immutable_hash = _hash_payload(
        {
            "package_type": package_type,
            "target_type": target_type,
            "target_id": str(target_id),
            "summary": summary,
            "evidence_json": evidence_json,
            "file_refs_json": _sanitize_node(file_refs or {}),
        }
    )
    evidence = CommercialEvidencePackage(
        client_id=client_id,
        package_type=package_type,
        target_type=target_type,
        target_id=str(target_id),
        summary=_sanitize_text(summary),
        evidence_json=evidence_json,
        file_refs_json=_sanitize_node(file_refs or {}),
        immutable_hash=immutable_hash,
        created_at=created_at,
    )
    db.add(evidence)

    # Phase 36: Encrypted Artifact
    if _settings.commercial_tenant_encryption_enabled:
        await _encryption_service.encrypt_payload(
            db,
            client_id,
            json.dumps(evidence_json),
            artifact_type="evidence",
            resource_type="evidence_package",
            resource_id=str(evidence.id),
            key_purpose="evidence",
        )

    await db.flush()
    return evidence


async def require_approval_chain(
    db: AsyncSession,
    *,
    client_id: uuid.UUID | None = None,
    policy: CommercialControlPolicy,
    target_type: str,
    target_id: str | uuid.UUID,
    requested_by: str,
    evidence_package_id: uuid.UUID | None = None,
) -> CommercialApprovalChain:
    existing_stmt = select(CommercialApprovalChain).where(
        CommercialApprovalChain.control_policy_id == policy.id,
        CommercialApprovalChain.target_type == target_type,
        CommercialApprovalChain.target_id == str(target_id),
        CommercialApprovalChain.status == "pending",
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        return existing
    chain = CommercialApprovalChain(
        client_id=client_id,
        control_policy_id=policy.id,
        target_type=target_type,
        target_id=str(target_id),
        status="pending",
        requested_by=requested_by,
        required_approver_count=max(1, int(policy.required_approver_count or 1)),
        approvals_json=[],
        rejections_json=[],
        evidence_package_id=evidence_package_id,
        created_at=utc_now(),
    )
    db.add(chain)
    await db.flush()
    return chain


def validate_segregation_of_duties(
    *,
    policy: CommercialControlPolicy,
    requester: str,
    approver: str,
    existing_approvals: list[dict[str, Any]] | None = None,
) -> None:
    approvals = existing_approvals or []
    if policy.segregation_required and requester == approver:
        raise ControlViolationError("segregation_of_duties_violation")
    if approvals and any(item.get("approver") == approver for item in approvals):
        raise ControlViolationError("duplicate_approval_not_allowed")


async def evaluate_control_policy(
    db: AsyncSession,
    *,
    control_area: str,
    action_type: str,
    target_type: str,
    target_id: str | uuid.UUID,
    actor: str,
    package_type: str | None = None,
    summary: str | None = None,
    before_state: Any = None,
    after_state: Any = None,
    payload: Any = None,
    related_ids: dict[str, Any] | None = None,
    file_refs: dict[str, Any] | list[Any] | None = None,
    client_id: uuid.UUID | None = None,
) -> ControlDecision:
    settings = get_settings()
    mode = settings.commercial_compliance_mode
    if not settings.commercial_compliance_controls_enabled or mode == "disabled":
        return ControlDecision(False, "disabled", None, False, False, False, 0, False, False)

    stmt = (
        select(CommercialControlPolicy)
        .where(
            CommercialControlPolicy.enabled.is_(True),
            CommercialControlPolicy.control_area == control_area,
            CommercialControlPolicy.action_type == action_type,
        )
        .order_by(desc(CommercialControlPolicy.created_at))
    )
    policy = (await db.execute(stmt)).scalars().first()
    if policy is None:
        return ControlDecision(
            True,
            mode,
            None,
            False,
            settings.commercial_compliance_segregation_required,
            settings.commercial_compliance_require_evidence,
            settings.commercial_compliance_default_approver_count,
            False,
            False,
        )

    evidence_required = bool(
        policy.evidence_required or settings.commercial_compliance_require_evidence
    )
    evidence = None
    if evidence_required:
        evidence = await create_evidence_package(
            db,
            client_id=client_id,
            package_type=package_type or action_type,
            target_type=target_type,
            target_id=target_id,
            summary=summary or f"{control_area}:{action_type}",
            actor=actor,
            before_state=before_state,
            after_state=after_state,
            payload=payload,
            related_ids=related_ids,
            file_refs=file_refs,
        )

    required_approver_count = max(
        1,
        int(
            policy.required_approver_count or settings.commercial_compliance_default_approver_count
        ),
    )
    requires_approval = bool(policy.requires_approval)
    should_block = mode == "enforce" and requires_approval
    chain = None
    if requires_approval:
        chain = await require_approval_chain(
            db,
            client_id=client_id,
            policy=policy,
            target_type=target_type,
            target_id=target_id,
            requested_by=actor,
            evidence_package_id=evidence.id if evidence else None,
        )
    return ControlDecision(
        enabled=True,
        mode=mode,
        policy=policy,
        requires_approval=requires_approval,
        segregation_required=bool(policy.segregation_required),
        evidence_required=evidence_required,
        required_approver_count=required_approver_count,
        should_block=should_block,
        pending_approval=bool(should_block and chain is not None),
        approval_chain=chain,
        evidence_package=evidence,
    )


async def approve_action(
    db: AsyncSession,
    *,
    chain_id: uuid.UUID,
    approver: str,
    notes: str | None = None,
) -> CommercialApprovalChain:
    chain = await db.get(CommercialApprovalChain, chain_id)
    if chain is None:
        raise ControlViolationError("approval_chain_not_found")
    policy = await db.get(CommercialControlPolicy, chain.control_policy_id)
    if policy is None:
        raise ControlViolationError("control_policy_not_found")
    approvals = list(chain.approvals_json or [])
    validate_segregation_of_duties(
        policy=policy, requester=chain.requested_by, approver=approver, existing_approvals=approvals
    )
    approvals.append(
        {
            "approver": approver,
            "notes": _sanitize_text(notes),
            "approved_at": utc_now().isoformat(),
        }
    )
    chain.approvals_json = approvals
    if len(approvals) >= max(1, chain.required_approver_count):
        unique_approvers = {item.get("approver") for item in approvals if item.get("approver")}
        if policy.segregation_required and unique_approvers == {chain.requested_by}:
            raise ControlViolationError("segregation_of_duties_violation")
        chain.status = "approved"
        chain.decided_at = utc_now()
    await db.flush()
    return chain


async def reject_action(
    db: AsyncSession,
    *,
    chain_id: uuid.UUID,
    approver: str,
    reason: str,
) -> CommercialApprovalChain:
    chain = await db.get(CommercialApprovalChain, chain_id)
    if chain is None:
        raise ControlViolationError("approval_chain_not_found")
    rejections = list(chain.rejections_json or [])
    rejections.append(
        {
            "approver": approver,
            "reason": _sanitize_text(reason),
            "rejected_at": utc_now().isoformat(),
        }
    )
    chain.rejections_json = rejections
    chain.status = "rejected"
    chain.decided_at = utc_now()
    await db.flush()
    return chain


async def create_attestation(
    db: AsyncSession,
    *,
    client_id: uuid.UUID | None = None,
    control_policy_id: uuid.UUID,
    attested_by: str,
    attestation_period_start: date,
    attestation_period_end: date,
    status: str = "pending",
    notes: str | None = None,
    evidence_package_id: uuid.UUID | None = None,
) -> CommercialControlAttestation:
    attestation = CommercialControlAttestation(
        client_id=client_id,
        control_policy_id=control_policy_id,
        attested_by=attested_by,
        attestation_period_start=attestation_period_start,
        attestation_period_end=attestation_period_end,
        status=status,
        notes=_sanitize_text(notes),
        evidence_package_id=evidence_package_id,
        created_at=utc_now(),
        attested_at=utc_now() if status in {"attested", "failed", "exception"} else None,
    )
    db.add(attestation)
    await db.flush()
    if status in {"failed", "exception"}:
        await open_exception(
            db,
            client_id=client_id,
            control_policy_id=control_policy_id,
            exception_type="attestation_failure",
            severity="high",
            description=notes or "Attestation failed",
            owner=attested_by,
        )
    return attestation


async def list_controls_needing_review(
    db: AsyncSession, *, as_of: date | None = None
) -> list[dict[str, Any]]:
    reference = as_of or utc_now().date()
    policies = (
        (
            await db.execute(
                select(CommercialControlPolicy)
                .where(CommercialControlPolicy.enabled.is_(True))
                .order_by(CommercialControlPolicy.name.asc())
            )
        )
        .scalars()
        .all()
    )
    items: list[dict[str, Any]] = []
    for policy in policies:
        latest_stmt = (
            select(CommercialControlAttestation)
            .where(CommercialControlAttestation.control_policy_id == policy.id)
            .order_by(desc(CommercialControlAttestation.attestation_period_end))
            .limit(1)
        )
        latest = (await db.execute(latest_stmt)).scalar_one_or_none()
        due = latest is None or latest.attestation_period_end < reference
        next_period_start = (
            reference if latest is None else latest.attestation_period_end + timedelta(days=1)
        )
        items.append(
            {
                "policy_id": str(policy.id),
                "policy_name": policy.name,
                "review_frequency": policy.review_frequency,
                "latest_status": latest.status if latest else None,
                "latest_period_end": latest.attestation_period_end.isoformat() if latest else None,
                "due": due,
                "suggested_period_start": next_period_start.isoformat(),
                "suggested_period_end": _frequency_window_end(
                    next_period_start, policy.review_frequency
                ).isoformat(),
            }
        )
    return items


async def open_exception(
    db: AsyncSession,
    *,
    client_id: uuid.UUID | None = None,
    exception_type: str,
    severity: str,
    description: str,
    control_policy_id: uuid.UUID | None = None,
    remediation_plan: str | None = None,
    owner: str | None = None,
    due_at: datetime | None = None,
) -> CommercialControlException:
    item = CommercialControlException(
        client_id=client_id,
        control_policy_id=control_policy_id,
        exception_type=exception_type,
        severity=severity,
        status="open",
        description=_sanitize_text(description),
        remediation_plan=_sanitize_text(remediation_plan),
        owner=owner,
        due_at=due_at,
        created_at=utc_now(),
    )
    db.add(item)
    await db.flush()
    return item


async def accept_exception(
    db: AsyncSession,
    *,
    exception_id: uuid.UUID,
    actor: str,
    remediation_plan: str | None = None,
) -> CommercialControlException:
    item = await db.get(CommercialControlException, exception_id)
    if item is None:
        raise ControlViolationError("control_exception_not_found")
    item.status = "accepted"
    item.owner = actor
    if remediation_plan:
        item.remediation_plan = _sanitize_text(remediation_plan)
    await db.flush()
    return item


async def remediate_exception(
    db: AsyncSession,
    *,
    exception_id: uuid.UUID,
    actor: str,
    remediation_plan: str | None = None,
) -> CommercialControlException:
    item = await db.get(CommercialControlException, exception_id)
    if item is None:
        raise ControlViolationError("control_exception_not_found")
    item.status = "remediated"
    item.owner = actor
    if remediation_plan:
        item.remediation_plan = _sanitize_text(remediation_plan)
    item.resolved_at = utc_now()
    await db.flush()
    return item


async def build_audit_report(
    db: AsyncSession, *, client_id: uuid.UUID | None = None
) -> dict[str, Any]:
    summary = await summarize_controls(db, client_id=client_id)
    policies = (
        (
            await db.execute(
                select(CommercialControlPolicy)
                .order_by(CommercialControlPolicy.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    chains_stmt = (
        select(CommercialApprovalChain)
        .order_by(CommercialApprovalChain.created_at.desc())
        .limit(100)
    )
    evidences_stmt = (
        select(CommercialEvidencePackage)
        .order_by(CommercialEvidencePackage.created_at.desc())
        .limit(100)
    )
    attestations_stmt = (
        select(CommercialControlAttestation)
        .order_by(CommercialControlAttestation.created_at.desc())
        .limit(100)
    )
    exceptions_stmt = (
        select(CommercialControlException)
        .order_by(CommercialControlException.created_at.desc())
        .limit(100)
    )
    if client_id is not None:
        chains_stmt = chains_stmt.where(CommercialApprovalChain.client_id == client_id)
        evidences_stmt = evidences_stmt.where(CommercialEvidencePackage.client_id == client_id)
        attestations_stmt = attestations_stmt.where(
            CommercialControlAttestation.client_id == client_id
        )
        exceptions_stmt = exceptions_stmt.where(CommercialControlException.client_id == client_id)
    chains = (await db.execute(chains_stmt)).scalars().all()
    evidences = (await db.execute(evidences_stmt)).scalars().all()
    attestations = (await db.execute(attestations_stmt)).scalars().all()
    exceptions = (await db.execute(exceptions_stmt)).scalars().all()
    return sanitize_report_payload(
        {
            "generated_at": utc_now().isoformat(),
            "summary": summary,
            "policies": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "control_area": item.control_area,
                    "action_type": item.action_type,
                    "enabled": item.enabled,
                    "requires_approval": item.requires_approval,
                    "segregation_required": item.segregation_required,
                    "evidence_required": item.evidence_required,
                }
                for item in policies
            ],
            "approval_chains": [
                {
                    "id": str(item.id),
                    "target_type": item.target_type,
                    "target_id": item.target_id,
                    "status": item.status,
                    "requested_by": item.requested_by,
                    "required_approver_count": item.required_approver_count,
                }
                for item in chains
            ],
            "evidence_packages": [
                {
                    "id": str(item.id),
                    "package_type": item.package_type,
                    "target_type": item.target_type,
                    "target_id": item.target_id,
                    "summary": item.summary,
                    "immutable_hash": item.immutable_hash,
                }
                for item in evidences
            ],
            "attestations": [
                {
                    "id": str(item.id),
                    "control_policy_id": str(item.control_policy_id),
                    "status": item.status,
                    "period_start": item.attestation_period_start.isoformat(),
                    "period_end": item.attestation_period_end.isoformat(),
                    "attested_by": item.attested_by,
                }
                for item in attestations
            ],
            "exceptions": [
                {
                    "id": str(item.id),
                    "control_policy_id": str(item.control_policy_id)
                    if item.control_policy_id
                    else None,
                    "exception_type": item.exception_type,
                    "severity": item.severity,
                    "status": item.status,
                    "owner": item.owner,
                    "due_at": item.due_at.isoformat() if item.due_at else None,
                }
                for item in exceptions
            ],
        }
    )


def render_audit_report_csv(report: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "id", "name", "status", "type", "owner"])
    for policy in report.get("policies", []):
        writer.writerow(
            [
                "policy",
                policy.get("id"),
                policy.get("name"),
                "enabled" if policy.get("enabled") else "disabled",
                policy.get("control_area"),
                "",
            ]
        )
    for chain in report.get("approval_chains", []):
        writer.writerow(
            [
                "approval_chain",
                chain.get("id"),
                chain.get("target_id"),
                chain.get("status"),
                chain.get("target_type"),
                chain.get("requested_by"),
            ]
        )
    for item in report.get("exceptions", []):
        writer.writerow(
            [
                "exception",
                item.get("id"),
                item.get("exception_type"),
                item.get("status"),
                item.get("severity"),
                item.get("owner"),
            ]
        )
    return output.getvalue()


def render_audit_report_html(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Compliance Audit Report</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; color: #111827; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 10px; padding: 12px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      th, td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
      th {{ background: #f3f4f6; }}
    </style>
  </head>
  <body>
    <h1>Compliance Audit Report</h1>
    <p>Generated at {html.escape(str(report.get("generated_at", "")))}</p>
    <div class="grid">
      <div class="card"><strong>Policies</strong><div>{summary.get("active_controls", 0)}</div></div>
      <div class="card"><strong>Pending Approvals</strong><div>{summary.get("pending_approval_chains", 0)}</div></div>
      <div class="card"><strong>Open Exceptions</strong><div>{summary.get("open_exceptions", 0)}</div></div>
      <div class="card"><strong>Pending Attestations</strong><div>{summary.get("pending_attestations", 0)}</div></div>
    </div>
    <h2>Exceptions</h2>
    <table>
      <thead><tr><th>ID</th><th>Type</th><th>Severity</th><th>Status</th><th>Owner</th></tr></thead>
      <tbody>
        {"".join(f"<tr><td>{html.escape(item.get('id', ''))}</td><td>{html.escape(item.get('exception_type', ''))}</td><td>{html.escape(item.get('severity', ''))}</td><td>{html.escape(item.get('status', ''))}</td><td>{html.escape(str(item.get('owner') or ''))}</td></tr>" for item in report.get("exceptions", []))}
      </tbody>
    </table>
  </body>
</html>"""


async def summarize_controls(
    db: AsyncSession, *, client_id: uuid.UUID | None = None
) -> dict[str, Any]:
    active_controls = (
        await db.execute(
            select(func.count(CommercialControlPolicy.id)).where(
                CommercialControlPolicy.enabled.is_(True)
            )
        )
    ).scalar() or 0
    pending_stmt = select(func.count(CommercialApprovalChain.id)).where(
        CommercialApprovalChain.status == "pending"
    )
    evidence_stmt = select(func.count(CommercialEvidencePackage.id)).where(
        CommercialEvidencePackage.created_at >= utc_now() - timedelta(days=7)
    )
    attestation_stmt = select(func.count(CommercialControlAttestation.id)).where(
        CommercialControlAttestation.status == "pending"
    )
    exception_stmt = select(func.count(CommercialControlException.id)).where(
        CommercialControlException.status.in_(["open", "accepted"])
    )
    if client_id is not None:
        pending_stmt = pending_stmt.where(CommercialApprovalChain.client_id == client_id)
        evidence_stmt = evidence_stmt.where(CommercialEvidencePackage.client_id == client_id)
        attestation_stmt = attestation_stmt.where(
            CommercialControlAttestation.client_id == client_id
        )
        exception_stmt = exception_stmt.where(CommercialControlException.client_id == client_id)
    pending_approval_chains = (await db.execute(pending_stmt)).scalar() or 0
    recent_evidence_packages = (await db.execute(evidence_stmt)).scalar() or 0
    pending_attestations = (await db.execute(attestation_stmt)).scalar() or 0
    open_exceptions = (await db.execute(exception_stmt)).scalar() or 0
    return {
        "active_controls": int(active_controls),
        "pending_approval_chains": int(pending_approval_chains),
        "recent_evidence_packages": int(recent_evidence_packages),
        "pending_attestations": int(pending_attestations),
        "open_exceptions": int(open_exceptions),
        "badges": [
            "APPROVAL_REQUIRED" if pending_approval_chains else None,
            "EVIDENCE_READY" if recent_evidence_packages else None,
            "EXCEPTION_OPEN" if open_exceptions else None,
            "ATTESTED" if not pending_attestations and active_controls else None,
        ],
    }


async def record_control_event(
    db: AsyncSession,
    *,
    action: str,
    status: str,
    payload: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    db.add(
        AdminActionLog(
            action=action,
            admin_role="system",
            payload_json=sanitize_report_payload(payload or {}),
            result_json=sanitize_report_payload(result or {}),
            status=status,
            created_at=utc_now(),
        )
    )


__all__ = [
    "ControlDecision",
    "ControlViolationError",
    "accept_exception",
    "approve_action",
    "build_audit_report",
    "create_attestation",
    "create_evidence_package",
    "evaluate_control_policy",
    "list_controls_needing_review",
    "open_exception",
    "record_control_event",
    "reject_action",
    "remediate_exception",
    "render_audit_report_csv",
    "render_audit_report_html",
    "require_approval_chain",
    "summarize_controls",
    "validate_segregation_of_duties",
]
