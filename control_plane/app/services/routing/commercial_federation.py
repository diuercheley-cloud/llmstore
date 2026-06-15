from __future__ import annotations

import csv
import html
import io
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx
from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_cluster_aggregate import CommercialClusterAggregate
from app.models.commercial.commercial_cluster_registry import CommercialClusterRegistry
from app.models.commercial.commercial_cluster_sync_log import CommercialClusterSyncLog
from app.models.commercial.commercial_federated_aggregate import CommercialFederatedAggregate
from app.services.routing.commercial_cluster_registry import (
    ensure_local_cluster_registered,
    list_clusters,
    mark_cluster_offline,
    register_cluster,
    update_cluster_status,
    validate_tenant_scope,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ALLOWED_AGGREGATE_FIELDS = {
    "bucket_start",
    "bucket_minutes",
    "provider",
    "model",
    "client_id",
    "tenant_id",
    "requests_count",
    "fallback_count",
    "block_count",
    "estimated_revenue_brl",
    "estimated_cost_brl",
    "actual_revenue_brl",
    "actual_cost_brl",
    "actual_margin_brl",
    "avg_latency_ms",
    "error_count",
    "received_at",
}
REJECTED_SECRET_FRAGMENTS = (
    "token",
    "secret",
    "password",
    "authorization",
    "api_key",
    "prompt",
    "response",
)


def _clean_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _field_contains_secret(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in REJECTED_SECRET_FRAGMENTS)


def _contains_rejected_secret(payload: Any, parent_key: str = "") -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if _field_contains_secret(str(key)):
                return True
            if _contains_rejected_secret(value, str(key)):
                return True
        return False
    if isinstance(payload, list):
        return any(_contains_rejected_secret(item, parent_key) for item in payload)
    if isinstance(payload, str):
        lowered = payload.lower()
        return "bearer " in lowered or lowered.startswith("sk-")
    return False


def _cluster_key(settings: Settings | None = None) -> str:
    cfg = settings or get_settings()
    return (cfg.commercial_cluster_id or "local").strip() or "local"


def _build_dedupe_key(
    source_cluster_id: str,
    bucket_start: str,
    provider: str | None,
    model: str | None,
    client_id: str | None,
    tenant_id: str | None,
) -> str:
    return "|".join(
        [
            source_cluster_id,
            bucket_start,
            provider or "-",
            model or "-",
            client_id or "-",
            tenant_id or "-",
        ]
    )


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


async def dedupe_federated_aggregate(db: AsyncSession, dedupe_key: str) -> bool:
    row = (
        await db.execute(
            select(CommercialFederatedAggregate.id).where(
                CommercialFederatedAggregate.dedupe_key == dedupe_key
            )
        )
    ).first()
    return row is not None


def _serialize_local_aggregate(
    row: CommercialClusterAggregate, *, source_cluster_id: str
) -> dict[str, Any]:
    bucket_start = row.bucket_start.isoformat()
    return {
        "source_cluster_id": source_cluster_id,
        "bucket_start": bucket_start,
        "bucket_minutes": int(row.bucket_minutes or 0),
        "provider": row.provider,
        "model": row.model,
        "client_id": row.client_id,
        "tenant_id": None,
        "requests_count": int(row.requests_count or 0),
        "fallback_count": int(row.fallback_count or 0),
        "block_count": int(row.block_count or 0),
        "estimated_revenue_brl": round(float(row.estimated_revenue_brl or 0), 4),
        "estimated_cost_brl": round(float(row.estimated_cost_brl or 0), 4),
        "actual_revenue_brl": round(float(row.actual_revenue_brl or 0), 4),
        "actual_cost_brl": round(float(row.actual_cost_brl or 0), 4),
        "actual_margin_brl": round(float(row.actual_margin_brl or 0), 4),
        "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
        "error_count": int(row.error_count or 0),
        "received_at": utc_now().isoformat(),
        "dedupe_key": _build_dedupe_key(
            source_cluster_id, bucket_start, row.provider, row.model, row.client_id, None
        ),
    }


async def export_local_aggregates_for_federation(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    await ensure_local_cluster_registered(db, settings=cfg)
    since = utc_now() - timedelta(hours=hours)
    rows = (
        (
            await db.execute(
                select(CommercialClusterAggregate)
                .where(CommercialClusterAggregate.bucket_start >= since)
                .order_by(CommercialClusterAggregate.bucket_start.asc())
            )
        )
        .scalars()
        .all()
    )
    payload = {
        "source_cluster_id": _cluster_key(cfg),
        "generated_at_utc": utc_now().isoformat(),
        "period_hours": hours,
        "aggregates": [
            _serialize_local_aggregate(row, source_cluster_id=_cluster_key(cfg)) for row in rows
        ],
    }
    return sanitize_report_payload(payload)


async def _create_sync_log(
    db: AsyncSession, *, source_cluster_id: str, sync_type: str
) -> CommercialClusterSyncLog:
    row = CommercialClusterSyncLog(
        source_cluster_id=source_cluster_id,
        sync_type=sync_type,
        status="failed",
        started_at=utc_now(),
        records_received=0,
        records_processed=0,
        records_duplicate=0,
    )
    db.add(row)
    await db.flush()
    return row


async def ingest_federated_aggregates(
    db: AsyncSession,
    payload: dict[str, Any],
    *,
    sync_type: str = "push",
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    if _contains_rejected_secret(payload):
        raise ValueError("payload contains secrets")
    source_cluster_id = str(payload.get("source_cluster_id") or "").strip() or "unknown"
    sync_log = await _create_sync_log(db, source_cluster_id=source_cluster_id, sync_type=sync_type)
    aggregates = payload.get("aggregates") or []
    sync_log.records_received = len(aggregates)
    if not isinstance(aggregates, list):
        sync_log.status = "failed"
        sync_log.error_message = "aggregates must be a list"
        sync_log.finished_at = utc_now()
        await db.flush()
        return {"accepted": False, "reason": "invalid_payload"}

    row = (
        await db.execute(
            select(CommercialClusterRegistry).where(
                CommercialClusterRegistry.cluster_id == source_cluster_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = await register_cluster(
            db,
            cluster_id=source_cluster_id,
            name=source_cluster_id,
            region=None,
            environment="local",
            status="active",
            tenant_scope_json={},
            metadata_json={"auto_registered": True},
            last_seen_at=utc_now(),
        )

    processed = 0
    duplicates = 0
    rejected = 0
    local_cluster_id = _cluster_key(cfg)
    allow_local_scope = source_cluster_id == local_cluster_id

    for raw_item in aggregates:
        if _contains_rejected_secret(raw_item):
            rejected += 1
            continue
        item = {key: raw_item.get(key) for key in ALLOWED_AGGREGATE_FIELDS if key in raw_item}
        bucket_start_raw = _clean_scalar(item.get("bucket_start"))
        bucket_start = _parse_datetime(bucket_start_raw)
        if not bucket_start:
            rejected += 1
            continue
        provider = _clean_scalar(item.get("provider"))
        model = _clean_scalar(item.get("model"))
        client_id = _clean_scalar(item.get("client_id"))
        tenant_id = _clean_scalar(item.get("tenant_id"))
        allowed, reason = validate_tenant_scope(
            row.tenant_scope_json, tenant_id, allow_local=allow_local_scope
        )
        if not allowed:
            rejected += 1
            sync_log.error_message = reason
            continue
        dedupe_key = _build_dedupe_key(
            source_cluster_id, bucket_start.isoformat(), provider, model, client_id, tenant_id
        )
        if await dedupe_federated_aggregate(db, dedupe_key):
            duplicates += 1
            continue
        received_at = _parse_datetime(item.get("received_at")) or utc_now()
        db.add(
            CommercialFederatedAggregate(
                source_cluster_id=source_cluster_id,
                bucket_start=bucket_start,
                bucket_minutes=int(item.get("bucket_minutes") or 0),
                provider=provider,
                model=model,
                client_id=client_id,
                tenant_id=tenant_id,
                requests_count=int(item.get("requests_count") or 0),
                fallback_count=int(item.get("fallback_count") or 0),
                block_count=int(item.get("block_count") or 0),
                estimated_revenue_brl=float(item.get("estimated_revenue_brl") or 0),
                estimated_cost_brl=float(item.get("estimated_cost_brl") or 0),
                actual_revenue_brl=float(item.get("actual_revenue_brl") or 0),
                actual_cost_brl=float(item.get("actual_cost_brl") or 0),
                actual_margin_brl=float(item.get("actual_margin_brl") or 0),
                avg_latency_ms=float(item.get("avg_latency_ms") or 0),
                error_count=int(item.get("error_count") or 0),
                received_at=received_at,
                dedupe_key=dedupe_key,
            )
        )
        processed += 1

    await update_cluster_status(
        db,
        cluster_id=source_cluster_id,
        status="active" if rejected == 0 else "degraded",
        last_seen_at=utc_now(),
        metadata_json=(row.metadata_json or {}),
    )
    sync_log.records_processed = processed
    sync_log.records_duplicate = duplicates
    sync_log.status = (
        "duplicate"
        if processed == 0 and duplicates > 0 and rejected == 0
        else ("partial" if rejected > 0 else "success")
    )
    if processed == 0 and duplicates == 0 and rejected > 0:
        sync_log.status = "failed"
    sync_log.finished_at = utc_now()
    await db.flush()
    return sanitize_report_payload(
        {
            "accepted": processed > 0 or duplicates > 0,
            "source_cluster_id": source_cluster_id,
            "records_received": len(aggregates),
            "records_processed": processed,
            "records_duplicate": duplicates,
            "records_rejected": rejected,
            "status": sync_log.status,
        }
    )


def _seed_cluster_rollup() -> dict[str, Any]:
    return {
        "requests_count": 0,
        "fallback_count": 0,
        "block_count": 0,
        "estimated_revenue_brl": 0.0,
        "estimated_cost_brl": 0.0,
        "actual_revenue_brl": 0.0,
        "actual_cost_brl": 0.0,
        "actual_margin_brl": 0.0,
        "error_count": 0,
        "latency_weighted_total": 0.0,
        "latency_weight": 0,
        "providers": set(),
    }


async def summarize_federated_overview(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    await ensure_local_cluster_registered(db, settings=cfg)
    since = utc_now() - timedelta(hours=hours)
    local_cluster_id = _cluster_key(cfg)

    local_rows = (
        (
            await db.execute(
                select(CommercialClusterAggregate).where(
                    CommercialClusterAggregate.bucket_start >= since
                )
            )
        )
        .scalars()
        .all()
    )
    federated_rows = (
        (
            await db.execute(
                select(CommercialFederatedAggregate).where(
                    CommercialFederatedAggregate.bucket_start >= since
                )
            )
        )
        .scalars()
        .all()
    )
    registry_rows = await list_clusters(db, settings=cfg)

    cluster_rollups: dict[str, dict[str, Any]] = defaultdict(_seed_cluster_rollup)
    for row in local_rows:
        bucket = cluster_rollups[local_cluster_id]
        bucket["requests_count"] += int(row.requests_count or 0)
        bucket["fallback_count"] += int(row.fallback_count or 0)
        bucket["block_count"] += int(row.block_count or 0)
        bucket["estimated_revenue_brl"] += float(row.estimated_revenue_brl or 0)
        bucket["estimated_cost_brl"] += float(row.estimated_cost_brl or 0)
        bucket["actual_revenue_brl"] += float(row.actual_revenue_brl or 0)
        bucket["actual_cost_brl"] += float(row.actual_cost_brl or 0)
        bucket["actual_margin_brl"] += float(row.actual_margin_brl or 0)
        bucket["error_count"] += int(row.error_count or 0)
        bucket["providers"].add(row.provider or "-")
        if row.avg_latency_ms is not None and row.requests_count:
            bucket["latency_weighted_total"] += float(row.avg_latency_ms or 0) * int(
                row.requests_count or 0
            )
            bucket["latency_weight"] += int(row.requests_count or 0)

    for row in federated_rows:
        bucket = cluster_rollups[row.source_cluster_id]
        bucket["requests_count"] += int(row.requests_count or 0)
        bucket["fallback_count"] += int(row.fallback_count or 0)
        bucket["block_count"] += int(row.block_count or 0)
        bucket["estimated_revenue_brl"] += float(row.estimated_revenue_brl or 0)
        bucket["estimated_cost_brl"] += float(row.estimated_cost_brl or 0)
        bucket["actual_revenue_brl"] += float(row.actual_revenue_brl or 0)
        bucket["actual_cost_brl"] += float(row.actual_cost_brl or 0)
        bucket["actual_margin_brl"] += float(row.actual_margin_brl or 0)
        bucket["error_count"] += int(row.error_count or 0)
        bucket["providers"].add(row.provider or "-")
        if row.avg_latency_ms is not None and row.requests_count:
            bucket["latency_weighted_total"] += float(row.avg_latency_ms or 0) * int(
                row.requests_count or 0
            )
            bucket["latency_weight"] += int(row.requests_count or 0)

    cluster_meta = {row["cluster_id"]: row for row in registry_rows}
    clusters = []
    anomalies = []
    for cluster_id in sorted(set(cluster_meta) | set(cluster_rollups)):
        stats = cluster_rollups[cluster_id]
        meta = cluster_meta.get(cluster_id, {})
        avg_latency = (
            (stats["latency_weighted_total"] / stats["latency_weight"])
            if stats["latency_weight"]
            else 0.0
        )
        cluster_entry = {
            "cluster_id": cluster_id,
            "name": meta.get("name", cluster_id),
            "region": meta.get("region"),
            "environment": meta.get("environment", "local"),
            "status": meta.get("status", "active"),
            "priority": meta.get("priority", 100),
            "tenant_scope_json": meta.get("tenant_scope_json", {}),
            "requests_count": stats["requests_count"],
            "fallback_count": stats["fallback_count"],
            "block_count": stats["block_count"],
            "estimated_revenue_brl": round(stats["estimated_revenue_brl"], 4),
            "estimated_cost_brl": round(stats["estimated_cost_brl"], 4),
            "actual_revenue_brl": round(stats["actual_revenue_brl"], 4),
            "actual_cost_brl": round(stats["actual_cost_brl"], 4),
            "actual_margin_brl": round(stats["actual_margin_brl"], 4),
            "avg_latency_ms": round(avg_latency, 2),
            "error_count": stats["error_count"],
            "providers": sorted(
                provider for provider in stats["providers"] if provider and provider != "-"
            ),
            "last_seen_at": meta.get("last_seen_at"),
        }
        clusters.append(cluster_entry)
        if cluster_entry["status"] in {"degraded", "offline"}:
            anomalies.append(
                {
                    "type": "cluster_status",
                    "cluster_id": cluster_id,
                    "message": f"cluster {cluster_id} is {cluster_entry['status']}",
                }
            )
        if cluster_entry["actual_margin_brl"] < 0:
            anomalies.append(
                {
                    "type": "negative_margin",
                    "cluster_id": cluster_id,
                    "message": f"cluster {cluster_id} has negative margin",
                }
            )

    totals = _seed_cluster_rollup()
    for item in clusters:
        totals["requests_count"] += item["requests_count"]
        totals["fallback_count"] += item["fallback_count"]
        totals["block_count"] += item["block_count"]
        totals["estimated_revenue_brl"] += item["estimated_revenue_brl"]
        totals["estimated_cost_brl"] += item["estimated_cost_brl"]
        totals["actual_revenue_brl"] += item["actual_revenue_brl"]
        totals["actual_cost_brl"] += item["actual_cost_brl"]
        totals["actual_margin_brl"] += item["actual_margin_brl"]
        totals["error_count"] += item["error_count"]
        totals["latency_weighted_total"] += item["avg_latency_ms"] * max(item["requests_count"], 1)
        totals["latency_weight"] += max(item["requests_count"], 1)

    overview = {
        "generated_at_utc": utc_now().isoformat(),
        "federation_enabled": cfg.commercial_federation_enabled,
        "federation_mode": cfg.commercial_federation_mode,
        "allow_push": cfg.commercial_federation_allow_push,
        "period_hours": hours,
        "clusters_registered": len(registry_rows),
        "clusters_reporting": len([item for item in clusters if item["requests_count"] > 0]),
        "requests_count": totals["requests_count"],
        "fallback_count": totals["fallback_count"],
        "block_count": totals["block_count"],
        "estimated_revenue_brl": round(totals["estimated_revenue_brl"], 4),
        "estimated_cost_brl": round(totals["estimated_cost_brl"], 4),
        "actual_revenue_brl": round(totals["actual_revenue_brl"], 4),
        "actual_cost_brl": round(totals["actual_cost_brl"], 4),
        "actual_margin_brl": round(totals["actual_margin_brl"], 4),
        "avg_latency_ms": round(
            (totals["latency_weighted_total"] / totals["latency_weight"])
            if totals["latency_weight"]
            else 0,
            2,
        ),
        "error_count": totals["error_count"],
        "clusters": clusters,
        "anomalies_cross_cluster": anomalies,
    }
    return sanitize_report_payload(overview)


async def compare_clusters(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    overview = await summarize_federated_overview(db, hours=hours, settings=settings)
    clusters = list(overview.get("clusters", []))
    if not clusters:
        return {
            "generated_at_utc": utc_now().isoformat(),
            "clusters": [],
            "comparisons": [],
            "anomalies": [],
        }
    sorted_by_margin = sorted(
        clusters, key=lambda item: item.get("actual_margin_brl", 0), reverse=True
    )
    baseline_latency = min(
        (item.get("avg_latency_ms", 0) for item in clusters if item.get("avg_latency_ms", 0) > 0),
        default=0,
    )
    comparisons = []
    anomalies = list(overview.get("anomalies_cross_cluster", []))
    for item in sorted_by_margin:
        comparison = {
            "cluster_id": item["cluster_id"],
            "margin_rank": sorted_by_margin.index(item) + 1,
            "actual_margin_brl": item["actual_margin_brl"],
            "actual_cost_brl": item["actual_cost_brl"],
            "avg_latency_ms": item["avg_latency_ms"],
            "requests_count": item["requests_count"],
            "providers": item.get("providers", []),
        }
        comparisons.append(comparison)
        if baseline_latency and item.get("avg_latency_ms", 0) >= baseline_latency * 2:
            anomalies.append(
                {
                    "type": "latency_regression",
                    "cluster_id": item["cluster_id"],
                    "message": f"cluster {item['cluster_id']} latency is >2x baseline",
                }
            )
    return sanitize_report_payload(
        {
            "generated_at_utc": utc_now().isoformat(),
            "clusters": clusters,
            "comparisons": comparisons,
            "anomalies": anomalies,
        }
    )


async def cleanup_federated_retention(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    cutoff = utc_now() - timedelta(days=cfg.commercial_federation_retention_days)
    aggregate_deleted = (
        await db.execute(
            delete(CommercialFederatedAggregate).where(
                CommercialFederatedAggregate.bucket_start < cutoff
            )
        )
    ).rowcount or 0
    sync_log_deleted = (
        await db.execute(
            delete(CommercialClusterSyncLog).where(CommercialClusterSyncLog.started_at < cutoff)
        )
    ).rowcount or 0
    await db.flush()
    return {
        "aggregate_deleted": aggregate_deleted,
        "sync_log_deleted": sync_log_deleted,
        "retention_days": cfg.commercial_federation_retention_days,
    }


async def export_federated_payload(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    overview = await summarize_federated_overview(db, hours=hours, settings=settings)
    compare = await compare_clusters(db, hours=hours, settings=settings)
    since = utc_now() - timedelta(hours=hours)
    local_cluster_id = _cluster_key(settings or get_settings())
    local_rows = (
        (
            await db.execute(
                select(CommercialClusterAggregate)
                .where(CommercialClusterAggregate.bucket_start >= since)
                .order_by(CommercialClusterAggregate.bucket_start.desc())
            )
        )
        .scalars()
        .all()
    )
    aggregates = (
        (
            await db.execute(
                select(CommercialFederatedAggregate)
                .where(CommercialFederatedAggregate.bucket_start >= since)
                .order_by(CommercialFederatedAggregate.bucket_start.desc())
            )
        )
        .scalars()
        .all()
    )
    return sanitize_report_payload(
        {
            "overview": overview,
            "clusters": overview.get("clusters", []),
            "aggregates": [
                {
                    "source_cluster_id": local_cluster_id,
                    "bucket_start": row.bucket_start.isoformat(),
                    "bucket_minutes": row.bucket_minutes,
                    "provider": row.provider,
                    "model": row.model,
                    "client_id": row.client_id,
                    "tenant_id": None,
                    "requests_count": row.requests_count,
                    "fallback_count": row.fallback_count,
                    "block_count": row.block_count,
                    "actual_margin_brl": round(float(row.actual_margin_brl or 0), 4),
                    "actual_cost_brl": round(float(row.actual_cost_brl or 0), 4),
                    "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
                    "error_count": row.error_count,
                }
                for row in local_rows
            ]
            + [
                {
                    "source_cluster_id": row.source_cluster_id,
                    "bucket_start": row.bucket_start.isoformat(),
                    "bucket_minutes": row.bucket_minutes,
                    "provider": row.provider,
                    "model": row.model,
                    "client_id": row.client_id,
                    "tenant_id": row.tenant_id,
                    "requests_count": row.requests_count,
                    "fallback_count": row.fallback_count,
                    "block_count": row.block_count,
                    "actual_margin_brl": round(float(row.actual_margin_brl or 0), 4),
                    "actual_cost_brl": round(float(row.actual_cost_brl or 0), 4),
                    "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
                    "error_count": row.error_count,
                }
                for row in aggregates
            ],
            "comparison": compare.get("comparisons", []),
            "anomalies_cross_cluster": compare.get("anomalies", []),
        }
    )


def export_federated_csv(report: dict[str, Any]) -> str:
    rows = report.get("aggregates", [])
    output = io.StringIO()
    fieldnames = (
        list(rows[0].keys())
        if rows
        else ["source_cluster_id", "bucket_start", "provider", "requests_count"]
    )
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def export_federated_html(report: dict[str, Any]) -> str:
    overview = report.get("overview", {})
    clusters = report.get("clusters", [])
    comparisons = report.get("comparison", [])
    anomalies = report.get("anomalies_cross_cluster", [])

    def _render_rows(rows: list[dict[str, Any]], fields: list[str]) -> str:
        if not rows:
            return "<p class='muted'>No data.</p>"
        head = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
        body = []
        for row in rows:
            cols = "".join(f"<td>{html.escape(str(row.get(field, '-')))}</td>" for field in fields)
            body.append(f"<tr>{cols}</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Commercial Federation</title>
    <style>
      body {{ font-family: Arial, sans-serif; background:#f7f7f7; color:#1f2937; margin:0; }}
      .page {{ max-width:1200px; margin:0 auto; padding:24px; }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
      .card {{ background:#fff; border:1px solid #d1d5db; border-radius:10px; padding:14px; }}
      .label {{ color:#6b7280; font-size:12px; text-transform:uppercase; }}
      .value {{ font-size:24px; font-weight:700; }}
      table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #d1d5db; }}
      th,td {{ padding:10px; border-bottom:1px solid #e5e7eb; text-align:left; font-size:14px; }}
      th {{ background:#f3f4f6; }}
      .muted {{ color:#6b7280; }}
    </style>
  </head>
  <body>
    <div class="page">
      <h1>Commercial Federation</h1>
      <p class="muted">Generated at {html.escape(str(overview.get("generated_at_utc", "-")))}</p>
      <div class="grid">
        <div class="card"><div class="label">Mode</div><div class="value">{html.escape(str(overview.get("federation_mode", "-")))}</div></div>
        <div class="card"><div class="label">Requests</div><div class="value">{html.escape(str(overview.get("requests_count", 0)))}</div></div>
        <div class="card"><div class="label">Margin</div><div class="value">R$ {html.escape(str(overview.get("actual_margin_brl", 0)))}</div></div>
        <div class="card"><div class="label">Clusters</div><div class="value">{html.escape(str(len(clusters)))}</div></div>
      </div>
      <h2>Clusters</h2>
      {_render_rows(clusters, ["cluster_id", "region", "environment", "status", "requests_count", "actual_margin_brl", "avg_latency_ms"])}
      <h2>Comparison</h2>
      {_render_rows(comparisons, ["cluster_id", "margin_rank", "actual_margin_brl", "actual_cost_brl", "avg_latency_ms", "requests_count"])}
      <h2>Anomalies</h2>
      {_render_rows(anomalies, ["type", "cluster_id", "message"])}
    </div>
  </body>
</html>"""


async def sync_federation_clusters(
    db: AsyncSession,
    *,
    sync_type: str = "manual",
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    await ensure_local_cluster_registered(db, settings=cfg)
    if (
        cfg.commercial_federation_mode not in {"push", "hybrid"}
        or not cfg.commercial_federation_allow_push
    ):
        return {
            "executed": False,
            "reason": "push_disabled",
            "mode": cfg.commercial_federation_mode,
            "results": [],
        }
    payload = await export_local_aggregates_for_federation(db, hours=24, settings=cfg)
    peers = (
        (
            await db.execute(
                select(CommercialClusterRegistry)
                .where(CommercialClusterRegistry.cluster_id != _cluster_key(cfg))
                .where(CommercialClusterRegistry.status != "disabled")
                .order_by(CommercialClusterRegistry.priority.asc())
            )
        )
        .scalars()
        .all()
    )
    results = []
    for peer in peers:
        if not peer.base_url:
            results.append(
                {"cluster_id": peer.cluster_id, "status": "skipped", "reason": "missing_base_url"}
            )
            continue
        try:
            headers = {"Content-Type": "application/json"}
            if cfg.commercial_federation_require_token and cfg.commercial_federation_shared_token:
                headers["X-Federation-Token"] = cfg.commercial_federation_shared_token
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{peer.base_url.rstrip('/')}/admin/routing/federation/ingest",
                    headers=headers,
                    json=payload,
                )
            if response.status_code >= 400:
                await update_cluster_status(db, cluster_id=peer.cluster_id, status="degraded")
                results.append(
                    {
                        "cluster_id": peer.cluster_id,
                        "status": "failed",
                        "http_status": response.status_code,
                    }
                )
                continue
            await update_cluster_status(
                db, cluster_id=peer.cluster_id, status="active", last_seen_at=utc_now()
            )
            results.append(
                {
                    "cluster_id": peer.cluster_id,
                    "status": "success",
                    "result": sanitize_report_payload(response.json()),
                }
            )
        except Exception as exc:
            logger.warning("federation sync failed for %s: %s", peer.cluster_id, exc)
            await mark_cluster_offline(db, cluster_id=peer.cluster_id)
            results.append({"cluster_id": peer.cluster_id, "status": "failed", "error": str(exc)})
    return {
        "executed": True,
        "mode": cfg.commercial_federation_mode,
        "results": sanitize_report_payload(results),
    }
