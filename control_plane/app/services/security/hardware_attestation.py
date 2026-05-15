from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial_sovereign_governance import CommercialHardwareAttestationRecord
from app.services.routing.commercial_report_export import sanitize_report_payload


def _evidence_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


async def collect_attestation_placeholder(
    db: AsyncSession,
    *,
    cluster_id: str,
    node_id: str | None = None,
    attestation_type: str = "placeholder",
    evidence_json: dict[str, Any] | None = None,
    status: str = "unknown",
    expires_at=None,
) -> CommercialHardwareAttestationRecord:
    sanitized = sanitize_report_payload(evidence_json or {})
    record = CommercialHardwareAttestationRecord(
        node_id=node_id,
        cluster_id=cluster_id,
        attestation_type=attestation_type,
        status=status,
        evidence_json=sanitized,
        evidence_hash=_evidence_hash(sanitized),
        expires_at=expires_at,
    )
    db.add(record)
    await db.flush()
    return record


async def verify_attestation_record(
    db: AsyncSession,
    record_id,
) -> CommercialHardwareAttestationRecord:
    record = await db.get(CommercialHardwareAttestationRecord, record_id)
    if not record:
        raise ValueError("Attestation record not found")
    expected_hash = _evidence_hash(record.evidence_json or {})
    if expected_hash != record.evidence_hash:
        record.status = "untrusted"
    elif record.expires_at and record.expires_at < utc_now():
        record.status = "expired"
    elif record.status == "unknown":
        record.status = "trusted"
    record.verified_at = utc_now()
    await db.flush()
    return record


async def enforce_attestation_policy(
    db: AsyncSession,
    *,
    cluster_id: str,
    mode: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    effective_mode = mode or settings.commercial_hardware_attestation_mode
    rows = await db.execute(
        select(CommercialHardwareAttestationRecord)
        .where(CommercialHardwareAttestationRecord.cluster_id == cluster_id)
        .order_by(CommercialHardwareAttestationRecord.created_at.desc())
    )
    records = rows.scalars().all()
    if not records:
        if effective_mode == "enforce":
            raise ValueError("No attestation records available for enforce mode")
        return {"allowed": effective_mode != "disabled", "status": "unknown", "records": 0}

    statuses = {record.status for record in records}
    if "untrusted" in statuses and effective_mode == "enforce":
        raise ValueError("Attestation enforcement blocked: untrusted node present")
    if "expired" in statuses and effective_mode == "enforce":
        raise ValueError("Attestation enforcement blocked: expired attestation present")
    return {
        "allowed": True,
        "status": "untrusted" if "untrusted" in statuses else ("expired" if "expired" in statuses else "trusted"),
        "records": len(records),
    }


async def summarize_attestation_status(db: AsyncSession) -> dict[str, Any]:
    total = (await db.execute(select(func.count(CommercialHardwareAttestationRecord.id)))).scalar() or 0
    recent = await db.execute(
        select(CommercialHardwareAttestationRecord).order_by(CommercialHardwareAttestationRecord.created_at.desc()).limit(20)
    )
    items = recent.scalars().all()
    by_status: dict[str, int] = {}
    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
    return {
        "total_records": int(total),
        "status_counts": by_status,
        "items": [
            {
                "id": str(item.id),
                "node_id": item.node_id,
                "cluster_id": item.cluster_id,
                "attestation_type": item.attestation_type,
                "status": item.status,
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }
