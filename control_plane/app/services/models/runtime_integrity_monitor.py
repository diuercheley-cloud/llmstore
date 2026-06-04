from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.commercial_governance_federation import CommercialGovernanceFederationPeer
from app.models.commercial_model_supply_chain import (
    CommercialModelIntegrityEvent,
    CommercialModelIntegrityScan,
    CommercialModelRevocationRecord,
    CommercialRuntimeModelAttestation,
    CommercialSignedModelRegistryEntry,
)
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.models.runtime_attestation import (
    collect_runtime_attestation,
    generate_boot_attestation,
    serialize_runtime_attestation,
)
from app.services.models.signed_model_registry import calculate_model_checksum, latest_registry_map
from app.services.routing.commercial_leader_election import renew_leader_lease, try_acquire_leader
from app.services.routing.commercial_node_heartbeat import resolve_node_identity
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

SCAN_TYPES = {"boot", "scheduled", "manual", "runtime_validation", "federated"}
INTEGRITY_EVENT_TYPES = {
    "model_integrity_scan_started",
    "model_integrity_verified",
    "model_integrity_drift_detected",
    "model_runtime_quarantined",
    "alias_drift_detected",
    "missing_model_detected",
}
ROUTING_LOADS = (
    selectinload(ModelRegistry.inference_backend),
    selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _immutable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _mask_checksum(value: str | None) -> str | None:
    if not value:
        return None
    return value[:12]


def _sanitize_text(value: str | None, *, limit: int = 255) -> str | None:
    if value is None:
        return None
    sanitized = sanitize_report_payload({"value": value}).get("value")
    if sanitized is None:
        return None
    return str(sanitized).replace("\n", " ").replace("\r", " ")[:limit]


def compare_checksum(expected_checksum: str | None, observed_checksum: str | None) -> dict[str, Any]:
    if not expected_checksum:
        return {"matched": observed_checksum is None, "reason": "missing_expected_checksum"}
    if expected_checksum == "manifest-only":
        return {"matched": True, "reason": "manifest_only"}
    if observed_checksum is None:
        return {"matched": False, "reason": "missing_observed_checksum"}
    if expected_checksum != observed_checksum:
        return {"matched": False, "reason": "checksum_mismatch"}
    return {"matched": True, "reason": "checksum_ok"}


async def _emit_integrity_event(
    db: AsyncSession,
    *,
    model_name: str,
    event_type: str,
    severity: str,
    summary: str,
    registry_entry_id=None,
    node_id: str | None = None,
    cluster_id: str | None = None,
    immutable_payload: dict[str, Any] | None = None,
) -> CommercialModelIntegrityEvent:
    if event_type not in INTEGRITY_EVENT_TYPES:
        raise ValueError(f"unsupported integrity event type: {event_type}")
    immutable_hash = _immutable_hash(immutable_payload) if immutable_payload else None
    row = CommercialModelIntegrityEvent(
        model_name=model_name,
        event_type=event_type,
        severity=severity,
        summary=_sanitize_text(summary, limit=1000) or event_type,
        registry_entry_id=registry_entry_id,
        node_id=node_id,
        cluster_id=cluster_id,
        immutable_hash=immutable_hash,
    )
    db.add(row)
    await db.flush()
    return row


async def _active_models(db: AsyncSession) -> list[ModelRegistry]:
    rows = await db.execute(
        select(ModelRegistry)
        .options(*ROUTING_LOADS)
        .where(ModelRegistry.is_active.is_(True))
        .order_by(ModelRegistry.is_default.desc(), ModelRegistry.created_at.asc())
    )
    return rows.scalars().all()


async def _latest_entry(db: AsyncSession, model: ModelRegistry) -> CommercialSignedModelRegistryEntry | None:
    rows = await db.execute(
        select(CommercialSignedModelRegistryEntry)
        .where(
            or_(
                CommercialSignedModelRegistryEntry.model_name == model.model_id,
                CommercialSignedModelRegistryEntry.model_alias == model.model_alias,
            )
        )
        .order_by(desc(CommercialSignedModelRegistryEntry.updated_at), desc(CommercialSignedModelRegistryEntry.created_at))
    )
    return rows.scalars().first()


async def _recent_failures(db: AsyncSession, entry: CommercialSignedModelRegistryEntry | None, model_name: str) -> int:
    stmt = (
        select(CommercialModelIntegrityScan)
        .where(CommercialModelIntegrityScan.model_name == model_name)
        .order_by(desc(CommercialModelIntegrityScan.created_at))
        .limit(3)
    )
    if entry is not None:
        stmt = stmt.where(CommercialModelIntegrityScan.registry_entry_id == entry.id)
    rows = (await db.execute(stmt)).scalars().all()
    return sum(1 for row in rows if row.integrity_status in {"error", "missing", "drift_detected", "quarantined"})


async def _has_active_revocation(db: AsyncSession, entry: CommercialSignedModelRegistryEntry | None, model_name: str) -> bool:
    stmt = select(CommercialModelRevocationRecord).where(
        CommercialModelRevocationRecord.model_name == model_name,
        CommercialModelRevocationRecord.revocation_type.in_(["checksum_mismatch", "crl"]),
    )
    if entry is not None:
        stmt = stmt.where(
            or_(
                CommercialModelRevocationRecord.registry_entry_id == entry.id,
                CommercialModelRevocationRecord.registry_entry_id.is_(None),
            )
        )
    return (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None


async def quarantine_runtime_model(
    db: AsyncSession,
    *,
    entry: CommercialSignedModelRegistryEntry | None,
    model: ModelRegistry | None = None,
    reason: str,
    node_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    model_name = entry.model_name if entry else (model.model_id if model else "unknown")
    if entry is not None:
        entry.trust_state = "quarantined"
        entry.updated_at = utc_now()
    if model is not None:
        model.status = "quarantined"
        model.updated_at = utc_now()
    await _emit_integrity_event(
        db,
        model_name=model_name,
        event_type="model_runtime_quarantined",
        severity="critical",
        summary=reason,
        registry_entry_id=entry.id if entry else None,
        node_id=node_id,
        cluster_id=cluster_id,
        immutable_payload={"reason": reason, "model_name": model_name},
    )
    await db.flush()
    return {"quarantined": True, "model_name": model_name, "reason": reason}


async def detect_alias_drift(
    db: AsyncSession,
    *,
    model: ModelRegistry,
    entry: CommercialSignedModelRegistryEntry | None,
    attestation: CommercialRuntimeModelAttestation | None = None,
    node_id: str | None = None,
    cluster_id: str | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    if entry is None:
        reasons.append("runtime_model_not_in_signed_registry")
    if entry and model.model_alias and entry.model_alias and model.model_alias != entry.model_alias:
        reasons.append("alias_value_changed")
    if entry and attestation and entry.manifest_hash and attestation.observed_manifest_hash:
        if entry.manifest_hash != attestation.observed_manifest_hash:
            reasons.append("alias_points_to_different_manifest")
    if entry and model.model_file and entry.model_file_path:
        observed_name = Path(model.model_file).name
        expected_name = Path(entry.model_file_path).name
        if observed_name != expected_name:
            reasons.append("alias_points_to_different_file")

    if reasons:
        await _emit_integrity_event(
            db,
            model_name=model.model_id,
            event_type="alias_drift_detected",
            severity="high",
            summary="alias drift detected: " + ", ".join(reasons),
            registry_entry_id=entry.id if entry else None,
            node_id=node_id,
            cluster_id=cluster_id,
            immutable_payload={"model_name": model.model_id, "reasons": reasons},
        )
    return {"alias_drift": bool(reasons), "reasons": reasons}


async def detect_runtime_drift(
    db: AsyncSession,
    *,
    model: ModelRegistry,
    entry: CommercialSignedModelRegistryEntry | None,
    scan: CommercialModelIntegrityScan,
    attestation: CommercialRuntimeModelAttestation,
    node_id: str | None = None,
    cluster_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    reasons: list[str] = []
    if scan.integrity_status == "missing":
        reasons.append("missing_model_file")
    if scan.expected_checksum and scan.observed_checksum and scan.expected_checksum != scan.observed_checksum:
        reasons.append("checksum_mismatch")
    if attestation.expected_manifest_hash and attestation.observed_manifest_hash:
        if attestation.expected_manifest_hash != attestation.observed_manifest_hash:
            reasons.append("manifest_mismatch")
    alias = await detect_alias_drift(
        db,
        model=model,
        entry=entry,
        attestation=attestation,
        node_id=node_id,
        cluster_id=cluster_id,
    )
    reasons.extend(alias["reasons"])

    repeated_failures = await _recent_failures(db, entry, model.model_id)
    if repeated_failures >= 3:
        reasons.append("repeated_scan_failures")
    if await _has_active_revocation(db, entry, model.model_id):
        reasons.append("revoked_checksum_active")

    should_quarantine = bool(reasons) and (
        cfg.commercial_model_integrity_auto_quarantine or "revoked_checksum_active" in reasons
    )
    if should_quarantine:
        await quarantine_runtime_model(
            db,
            entry=entry,
            model=model,
            reason="runtime integrity quarantine: " + ", ".join(reasons),
            node_id=node_id,
            cluster_id=cluster_id,
        )
        scan.integrity_status = "quarantined"
        attestation.attestation_status = "quarantined"
    elif reasons:
        await _emit_integrity_event(
            db,
            model_name=model.model_id,
            event_type="model_integrity_drift_detected",
            severity="high",
            summary="runtime drift detected: " + ", ".join(reasons),
            registry_entry_id=entry.id if entry else None,
            node_id=node_id,
            cluster_id=cluster_id,
            immutable_payload={"model_name": model.model_id, "reasons": reasons},
        )
        if scan.integrity_status != "missing":
            scan.integrity_status = "drift_detected"
        if attestation.attestation_status != "quarantined":
            attestation.attestation_status = "drift"
    else:
        await _emit_integrity_event(
            db,
            model_name=model.model_id,
            event_type="model_integrity_verified",
            severity="info",
            summary="runtime integrity verified",
            registry_entry_id=entry.id if entry else None,
            node_id=node_id,
            cluster_id=cluster_id,
            immutable_payload={"model_name": model.model_id, "scan_id": str(scan.id)},
        )
    await db.flush()
    return {"drift_detected": bool(reasons), "reasons": reasons, "quarantined": should_quarantine}


async def scan_model_file(
    db: AsyncSession,
    *,
    model: ModelRegistry,
    entry: CommercialSignedModelRegistryEntry | None = None,
    scan_type: str = "manual",
    node_id: str | None = None,
    cluster_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    if scan_type not in SCAN_TYPES:
        raise ValueError(f"unsupported scan_type: {scan_type}")

    start = perf_counter()
    entry = entry or await _latest_entry(db, model)
    model_name = model.model_id
    expected_checksum = entry.checksum_sha256 if entry else None
    runtime_path = Path(model.model_file) if Path(model.model_file).is_absolute() else Path(cfg.models_dir) / model.model_file
    metadata_json = {
        "model_alias": model.model_alias,
        "backend_name": model.inference_backend.name if model.inference_backend else None,
        "route_count": len(model.backend_routes or []),
    }
    scan = CommercialModelIntegrityScan(
        registry_entry_id=entry.id if entry else None,
        model_name=model_name,
        scan_type=scan_type,
        expected_checksum=expected_checksum,
        integrity_status="error",
        node_id=node_id,
        cluster_id=cluster_id,
        metadata_json=sanitize_report_payload(metadata_json),
    )
    db.add(scan)
    await db.flush()
    await _emit_integrity_event(
        db,
        model_name=model_name,
        event_type="model_integrity_scan_started",
        severity="info",
        summary=f"{scan_type} scan started",
        registry_entry_id=entry.id if entry else None,
        node_id=node_id,
        cluster_id=cluster_id,
        immutable_payload={"model_name": model_name, "scan_type": scan_type},
    )

    if not str(model.model_file or "").strip():
        scan.integrity_status = "verified"
        scan.scan_duration_ms = int((perf_counter() - start) * 1000)
        scan.metadata_json = sanitize_report_payload(metadata_json | {"reason": "manifest_only"})
        attestation = await collect_runtime_attestation(
            db,
            model=model,
            entry=entry,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=cfg,
        )
        drift = await detect_runtime_drift(
            db,
            model=model,
            entry=entry,
            scan=scan,
            attestation=attestation,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=cfg,
        )
        return {"scan": scan, "attestation": attestation, "drift": drift}

    if not runtime_path.exists():
        scan.integrity_status = "missing"
        scan.scan_duration_ms = int((perf_counter() - start) * 1000)
        scan.metadata_json = sanitize_report_payload(metadata_json | {"missing_file": runtime_path.name})
        await _emit_integrity_event(
            db,
            model_name=model_name,
            event_type="missing_model_detected",
            severity="critical",
            summary="runtime model file missing",
            registry_entry_id=entry.id if entry else None,
            node_id=node_id,
            cluster_id=cluster_id,
            immutable_payload={"model_name": model_name, "file_name": runtime_path.name},
        )
        attestation = await collect_runtime_attestation(
            db,
            model=model,
            entry=entry,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=cfg,
        )
        drift = await detect_runtime_drift(
            db,
            model=model,
            entry=entry,
            scan=scan,
            attestation=attestation,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=cfg,
        )
        return {"scan": scan, "attestation": attestation, "drift": drift}

    observed_checksum = await calculate_model_checksum(str(runtime_path))
    scan.observed_checksum = observed_checksum
    check = compare_checksum(expected_checksum, observed_checksum)
    scan.integrity_status = "verified" if check["matched"] else "drift_detected"
    scan.scan_duration_ms = int((perf_counter() - start) * 1000)
    scan.metadata_json = sanitize_report_payload(metadata_json | {"reason": check["reason"]})

    attestation = await collect_runtime_attestation(
        db,
        model=model,
        entry=entry,
        node_id=node_id,
        cluster_id=cluster_id,
        settings=cfg,
    )
    drift = await detect_runtime_drift(
        db,
        model=model,
        entry=entry,
        scan=scan,
        attestation=attestation,
        node_id=node_id,
        cluster_id=cluster_id,
        settings=cfg,
    )
    return {"scan": scan, "attestation": attestation, "drift": drift}


async def scan_registered_models(
    db: AsyncSession,
    *,
    scan_type: str = "manual",
    node_id: str | None = None,
    cluster_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    models = await _active_models(db)
    registry_map = await latest_registry_map(db)
    scans: list[CommercialModelIntegrityScan] = []
    attestations: list[CommercialRuntimeModelAttestation] = []
    drifted = 0
    quarantined = 0

    if scan_type == "boot":
        await generate_boot_attestation(
            db,
            models,
            registry_map,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=cfg,
        )

    for model in models:
        entry = registry_map.get(model.model_alias or "") or registry_map.get(model.model_id)
        result = await scan_model_file(
            db,
            model=model,
            entry=entry,
            scan_type=scan_type,
            node_id=node_id,
            cluster_id=cluster_id,
            settings=cfg,
        )
        scan = result["scan"]
        attestation = result["attestation"]
        scans.append(scan)
        attestations.append(attestation)
        if result["drift"]["drift_detected"]:
            drifted += 1
        if result["drift"]["quarantined"]:
            quarantined += 1

    summary = {
        "scan_type": scan_type,
        "models_scanned": len(scans),
        "verified": sum(1 for item in scans if item.integrity_status == "verified"),
        "drift_detected": drifted,
        "quarantined": quarantined,
        "missing": sum(1 for item in scans if item.integrity_status == "missing"),
        "node_id": node_id,
        "cluster_id": cluster_id,
    }
    return sanitize_report_payload(summary)


async def summarize_integrity_status(db: AsyncSession, *, client_id=None) -> dict[str, Any]:
    latest_scans = (
        await db.execute(
            select(CommercialModelIntegrityScan)
            .order_by(desc(CommercialModelIntegrityScan.created_at))
            .limit(100)
        )
    ).scalars().all()
    latest_events = (
        await db.execute(
            select(CommercialModelIntegrityEvent)
            .order_by(desc(CommercialModelIntegrityEvent.created_at))
            .limit(100)
        )
    ).scalars().all()
    latest_attestations = (
        await db.execute(
            select(CommercialRuntimeModelAttestation)
            .order_by(desc(CommercialRuntimeModelAttestation.attested_at))
            .limit(100)
        )
    ).scalars().all()
    peer_rows = (
        await db.execute(
            select(CommercialGovernanceFederationPeer).order_by(desc(CommercialGovernanceFederationPeer.updated_at))
        )
    ).scalars().all()

    status_counts: dict[str, int] = {}
    for row in latest_scans:
        status_counts[row.integrity_status] = status_counts.get(row.integrity_status, 0) + 1

    attestation_counts: dict[str, int] = {}
    for row in latest_attestations:
        attestation_counts[row.attestation_status] = attestation_counts.get(row.attestation_status, 0) + 1

    quarantined_models = sorted({row.model_name for row in latest_scans if row.integrity_status == "quarantined"})
    missing_models = sorted({row.model_name for row in latest_scans if row.integrity_status == "missing"})
    alias_drift_models = sorted({row.model_name for row in latest_events if row.event_type == "alias_drift_detected"})
    drift_models = sorted({row.model_name for row in latest_events if row.event_type == "model_integrity_drift_detected"})

    items = []
    for row in latest_scans[:20]:
        items.append(
            sanitize_report_payload(
                {
                    "id": str(row.id),
                    "registry_entry_id": str(row.registry_entry_id) if row.registry_entry_id else None,
                    "model_name": row.model_name,
                    "scan_type": row.scan_type,
                    "expected_checksum": _mask_checksum(row.expected_checksum),
                    "observed_checksum": _mask_checksum(row.observed_checksum),
                    "integrity_status": row.integrity_status,
                    "scan_duration_ms": row.scan_duration_ms,
                    "node_id": row.node_id,
                    "cluster_id": row.cluster_id,
                    "metadata_json": row.metadata_json or {},
                    "created_at": row.created_at.isoformat(),
                }
            )
        )

    events = [
        sanitize_report_payload(
            {
                "id": str(row.id),
                "model_name": row.model_name,
                "event_type": row.event_type,
                "severity": row.severity,
                "summary": row.summary,
                "registry_entry_id": str(row.registry_entry_id) if row.registry_entry_id else None,
                "node_id": row.node_id,
                "cluster_id": row.cluster_id,
                "immutable_hash": _mask_checksum(row.immutable_hash),
                "created_at": row.created_at.isoformat(),
            }
        )
        for row in latest_events[:20]
    ]
    federated_integrity = {
        "local_cluster_id": get_settings().commercial_cluster_id,
        "peers": [
            {
                "peer_cluster_id": row.peer_cluster_id,
                "status": row.status,
                "environment": row.environment,
                "region": row.region,
            }
            for row in peer_rows[:20]
        ],
        "peer_count": len(peer_rows),
    }
    return sanitize_report_payload(
        {
            "scan_counts": status_counts,
            "attestation_counts": attestation_counts,
            "quarantined_models": quarantined_models,
            "missing_models": missing_models,
            "drift_models": drift_models,
            "alias_drift_models": alias_drift_models,
            "latest_scans": items,
            "integrity_timeline": events,
            "latest_attestations": [serialize_runtime_attestation(row) for row in latest_attestations[:20]],
            "federated_integrity": federated_integrity,
            "client_scope_applied": bool(client_id),
        }
    )


async def runtime_integrity_monitor_loop(stop_event: asyncio.Event) -> None:
    cfg = get_settings()
    if not cfg.commercial_model_integrity_monitor_enabled:
        return
    identity = resolve_node_identity(cfg)
    lease_token: int | None = None
    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                lease = await try_acquire_leader(
                    session,
                    cluster_id=cfg.cluster_id,
                    leader_role="scheduler",
                    node_id=identity["node_id"],
                    metadata_json={"job": "runtime_integrity_monitor"},
                    settings=cfg,
                )
                if lease.get("acquired"):
                    lease_token = int(lease["lease"]["lease_token"])
                    await renew_leader_lease(
                        session,
                        cluster_id=cfg.cluster_id,
                        leader_role="scheduler",
                        node_id=identity["node_id"],
                        lease_token=lease_token,
                        metadata_json={"job": "runtime_integrity_monitor"},
                        settings=cfg,
                    )
                    await scan_registered_models(
                        session,
                        scan_type="scheduled",
                        node_id=identity["node_id"],
                        cluster_id=cfg.cluster_id,
                        settings=cfg,
                    )
                await session.commit()
        except Exception as exc:
            logger.exception("runtime integrity monitor failed", extra={"extra_data": {"error": str(exc)}})
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=cfg.commercial_model_integrity_scan_interval_seconds)
        except asyncio.TimeoutError:
            continue
