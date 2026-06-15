from __future__ import annotations

import csv
import html
import io
import json
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_cluster_aggregate import CommercialClusterAggregate
from app.models.commercial.commercial_node_heartbeat import CommercialNodeHeartbeat
from app.models.commercial.commercial_routing_event import CommercialRoutingEvent
from app.models.commercial.commercial_routing_event_ingest import CommercialRoutingEventIngest
from app.services.routing.commercial_leader_election import validate_fencing_token
from app.services.routing.commercial_node_heartbeat import summarize_cluster_health
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _floor_bucket(value: datetime, bucket_minutes: int) -> datetime:
    base = _as_utc(value)
    minute = (base.minute // bucket_minutes) * bucket_minutes
    return base.replace(minute=minute, second=0, microsecond=0)


async def _resolve_event_map(
    db: AsyncSession,
    ingests: list[CommercialRoutingEventIngest],
) -> dict[str, CommercialRoutingEvent]:
    request_ids = {row.request_id for row in ingests if row.request_id}
    correlation_ids = {row.correlation_id for row in ingests if row.correlation_id}
    if not request_ids and not correlation_ids:
        return {}
    stmt = select(CommercialRoutingEvent)
    filters = []
    if request_ids:
        filters.append(CommercialRoutingEvent.request_id.in_(request_ids))
    if correlation_ids:
        filters.append(CommercialRoutingEvent.correlation_id.in_(correlation_ids))
    if len(filters) == 1:
        stmt = stmt.where(filters[0])
    else:
        from sqlalchemy import or_

        stmt = stmt.where(or_(*filters))
    result = await db.execute(stmt)
    event_map: dict[str, CommercialRoutingEvent] = {}
    for event in result.scalars().all():
        if event.request_id:
            event_map[f"req:{event.request_id}"] = event
        if event.correlation_id:
            event_map[f"corr:{event.correlation_id}"] = event
    return event_map


def _metrics_from_sources(
    ingest: CommercialRoutingEventIngest, event: CommercialRoutingEvent | None
) -> dict[str, Any]:
    payload = ingest.payload_json or {}
    provider = (event.selected_provider if event else None) or payload.get("selected_provider")
    model = (
        (event.selected_model if event else None)
        or payload.get("selected_model")
        or payload.get("model_requested")
    )
    client_id = str(event.client_id) if event and event.client_id else payload.get("client_id")
    estimated_revenue_brl = float(
        (event.estimated_revenue_brl if event else None)
        or payload.get("estimated_revenue_brl")
        or 0
    )
    estimated_cost_brl = float(
        (event.estimated_cost_brl if event else None) or payload.get("estimated_cost_brl") or 0
    )
    actual_revenue_brl = float(
        (event.actual_revenue_brl if event else None) or payload.get("actual_revenue_brl") or 0
    )
    actual_cost_brl = float(
        (event.actual_cost_brl if event else None) or payload.get("actual_cost_brl") or 0
    )
    actual_margin_brl = float(
        (event.actual_margin_brl if event else None)
        or payload.get("actual_margin_brl")
        or (actual_revenue_brl - actual_cost_brl)
    )
    latency_ms = (event.latency_ms if event else None) or payload.get("latency_ms")
    fallback_used = bool(
        (event.fallback_used if event else None) or payload.get("fallback_used", False)
    )
    blocked = bool((event.blocked if event else None) or payload.get("blocked", False))
    error_present = bool(
        (event.error_type if event else None)
        or payload.get("error_type")
        or payload.get("error_code")
    )
    return {
        "provider": provider,
        "model": model,
        "client_id": str(client_id) if client_id else None,
        "estimated_revenue_brl": estimated_revenue_brl,
        "estimated_cost_brl": estimated_cost_brl,
        "actual_revenue_brl": actual_revenue_brl,
        "actual_cost_brl": actual_cost_brl,
        "actual_margin_brl": actual_margin_brl,
        "latency_ms": float(latency_ms or 0),
        "fallback_used": fallback_used,
        "blocked": blocked,
        "error_present": error_present,
    }


async def aggregate_bucket(
    db: AsyncSession,
    bucket_start: datetime,
    *,
    bucket_minutes: int | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    bucket_minutes = bucket_minutes or cfg.commercial_analytics_aggregation_bucket_minutes
    bucket_start = _floor_bucket(bucket_start, bucket_minutes)
    bucket_end = bucket_start + timedelta(minutes=bucket_minutes)

    await db.execute(
        delete(CommercialClusterAggregate).where(
            CommercialClusterAggregate.bucket_start == bucket_start,
            CommercialClusterAggregate.bucket_minutes == bucket_minutes,
        )
    )

    ingest_result = await db.execute(
        select(CommercialRoutingEventIngest).where(
            CommercialRoutingEventIngest.status == "processed"
        )
    )
    ingests = [
        row
        for row in ingest_result.scalars().all()
        if row.received_at and bucket_start <= _as_utc(row.received_at) < bucket_end
    ]
    event_map = await _resolve_event_map(db, ingests)

    groups: dict[tuple[str | None, str | None, str | None, str | None], dict[str, Any]] = (
        defaultdict(
            lambda: {
                "requests_count": 0,
                "fallback_count": 0,
                "block_count": 0,
                "estimated_revenue_brl": 0.0,
                "estimated_cost_brl": 0.0,
                "actual_revenue_brl": 0.0,
                "actual_cost_brl": 0.0,
                "actual_margin_brl": 0.0,
                "latencies": [],
                "error_count": 0,
            }
        )
    )

    for ingest in ingests:
        event = event_map.get(f"req:{ingest.request_id}") or event_map.get(
            f"corr:{ingest.correlation_id}"
        )
        metrics = _metrics_from_sources(ingest, event)
        key = (ingest.node_id, metrics["provider"], metrics["model"], metrics["client_id"])
        bucket = groups[key]
        bucket["requests_count"] += 1
        bucket["fallback_count"] += int(metrics["fallback_used"])
        bucket["block_count"] += int(metrics["blocked"])
        bucket["estimated_revenue_brl"] += metrics["estimated_revenue_brl"]
        bucket["estimated_cost_brl"] += metrics["estimated_cost_brl"]
        bucket["actual_revenue_brl"] += metrics["actual_revenue_brl"]
        bucket["actual_cost_brl"] += metrics["actual_cost_brl"]
        bucket["actual_margin_brl"] += metrics["actual_margin_brl"]
        bucket["error_count"] += int(metrics["error_present"])
        if metrics["latency_ms"] > 0:
            bucket["latencies"].append(metrics["latency_ms"])

    for (node_id, provider, model, client_id), stats in groups.items():
        aggregate = CommercialClusterAggregate(
            bucket_start=bucket_start,
            bucket_minutes=bucket_minutes,
            node_id=node_id,
            provider=provider,
            model=model,
            client_id=client_id,
            requests_count=stats["requests_count"],
            fallback_count=stats["fallback_count"],
            block_count=stats["block_count"],
            estimated_revenue_brl=stats["estimated_revenue_brl"],
            estimated_cost_brl=stats["estimated_cost_brl"],
            actual_revenue_brl=stats["actual_revenue_brl"],
            actual_cost_brl=stats["actual_cost_brl"],
            actual_margin_brl=stats["actual_margin_brl"],
            avg_latency_ms=(sum(stats["latencies"]) / len(stats["latencies"]))
            if stats["latencies"]
            else 0,
            error_count=stats["error_count"],
        )
        db.add(aggregate)

    await db.flush()
    return {
        "bucket_start": bucket_start.isoformat(),
        "bucket_minutes": bucket_minutes,
        "source_events": len(ingests),
        "aggregate_rows": len(groups),
    }


async def aggregate_recent(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    bucket_minutes = cfg.commercial_analytics_aggregation_bucket_minutes
    end = _floor_bucket(utc_now(), bucket_minutes)
    start = _floor_bucket(end - timedelta(hours=hours), bucket_minutes)
    buckets = 0
    cursor = start
    while cursor <= end:
        await aggregate_bucket(db, cursor, bucket_minutes=bucket_minutes, settings=cfg)
        buckets += 1
        cursor += timedelta(minutes=bucket_minutes)
    return {
        "hours": hours,
        "bucket_minutes": bucket_minutes,
        "buckets_rebuilt": buckets,
    }


async def rebuild_aggregates(
    db: AsyncSession,
    *,
    hours: int = 24,
    lease_token: int | None = None,
    cluster_id: str | None = None,
    node_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    if lease_token is not None and cluster_id and node_id:
        valid = await validate_fencing_token(
            db,
            cluster_id=cluster_id,
            leader_role="aggregator",
            lease_token=lease_token,
            node_id=node_id,
            settings=cfg,
        )
        if not valid:
            return {"executed": False, "reason": "fencing_rejected", "lease_token": lease_token}
    return await aggregate_recent(db, hours=hours, settings=settings)


async def cleanup_old_analytics(
    db: AsyncSession,
    *,
    lease_token: int | None = None,
    cluster_id: str | None = None,
    node_id: str | None = None,
    settings: Settings | None = None,
) -> dict[str, int]:
    cfg = settings or get_settings()
    if lease_token is not None and cluster_id and node_id:
        valid = await validate_fencing_token(
            db,
            cluster_id=cluster_id,
            leader_role="aggregator",
            lease_token=lease_token,
            node_id=node_id,
            settings=cfg,
        )
        if not valid:
            return {
                "ingest_deleted": 0,
                "aggregate_deleted": 0,
                "heartbeat_deleted": 0,
                "retention_days": cfg.commercial_analytics_retention_days,
                "executed": False,
                "reason": "fencing_rejected",
            }
    cutoff = utc_now() - timedelta(days=cfg.commercial_analytics_retention_days)

    ingest_deleted = (
        await db.execute(
            delete(CommercialRoutingEventIngest).where(
                CommercialRoutingEventIngest.received_at < cutoff
            )
        )
    ).rowcount or 0
    aggregate_deleted = (
        await db.execute(
            delete(CommercialClusterAggregate).where(
                CommercialClusterAggregate.bucket_start < cutoff
            )
        )
    ).rowcount or 0
    heartbeat_deleted = (
        await db.execute(
            delete(CommercialNodeHeartbeat).where(CommercialNodeHeartbeat.last_seen_at < cutoff)
        )
    ).rowcount or 0
    await db.flush()
    return {
        "ingest_deleted": ingest_deleted,
        "aggregate_deleted": aggregate_deleted,
        "heartbeat_deleted": heartbeat_deleted,
        "retention_days": cfg.commercial_analytics_retention_days,
        "executed": True,
    }


async def get_cluster_overview(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    from app.services.routing.commercial_event_ingest import process_pending_events

    await process_pending_events(db, settings=cfg)
    await aggregate_recent(db, hours=hours, settings=cfg)
    health = await summarize_cluster_health(db, settings=cfg)

    since = utc_now() - timedelta(hours=hours)
    result = await db.execute(
        select(CommercialClusterAggregate).where(CommercialClusterAggregate.bucket_start >= since)
    )
    rows = result.scalars().all()

    overview = {
        "cluster_id": cfg.cluster_id,
        "generated_at_utc": utc_now().isoformat(),
        "period_hours": hours,
        "distributed_enabled": cfg.commercial_distributed_analytics_enabled,
        "health": health,
        "requests_count": 0,
        "fallback_count": 0,
        "block_count": 0,
        "estimated_revenue_brl": 0.0,
        "estimated_cost_brl": 0.0,
        "actual_revenue_brl": 0.0,
        "actual_cost_brl": 0.0,
        "actual_margin_brl": 0.0,
        "error_count": 0,
        "avg_latency_ms": 0.0,
        "estimated_vs_actual_drift_brl": 0.0,
        "nodes": [],
        "providers": [],
        "aggregates": [],
        "anomalies": [],
        "ha": None,
    }
    if not rows:
        try:
            from app.services.routing.commercial_leader_election import get_current_leader

            leaders = []
            for role in ["scheduler", "aggregator", "reporter", "calibration", "canary", "global"]:
                leader = await get_current_leader(
                    db, cluster_id=cfg.cluster_id, leader_role=role, settings=cfg
                )
                if leader:
                    leaders.append(leader)
            overview["ha"] = {"cluster_id": cfg.cluster_id, "leaders": leaders}
        except Exception as exc:
            logger.debug("cluster overview ha summary unavailable: %s", exc)
        return overview

    latency_weight = 0
    node_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "requests": 0,
            "margin": 0.0,
            "fallbacks": 0,
            "blocks": 0,
            "errors": 0,
            "last_bucket": None,
        }
    )
    provider_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"requests": 0, "margin": 0.0, "cost": 0.0}
    )
    aggregate_rows = []
    drift_abs = 0.0

    for row in rows:
        overview["requests_count"] += row.requests_count or 0
        overview["fallback_count"] += row.fallback_count or 0
        overview["block_count"] += row.block_count or 0
        overview["estimated_revenue_brl"] += float(row.estimated_revenue_brl or 0)
        overview["estimated_cost_brl"] += float(row.estimated_cost_brl or 0)
        overview["actual_revenue_brl"] += float(row.actual_revenue_brl or 0)
        overview["actual_cost_brl"] += float(row.actual_cost_brl or 0)
        overview["actual_margin_brl"] += float(row.actual_margin_brl or 0)
        overview["error_count"] += row.error_count or 0
        if row.avg_latency_ms is not None and row.requests_count:
            overview["avg_latency_ms"] += float(row.avg_latency_ms or 0) * row.requests_count
            latency_weight += row.requests_count
        drift_abs += abs(float((row.estimated_revenue_brl or 0) - (row.actual_revenue_brl or 0)))

        if row.node_id:
            node_bucket = node_stats[row.node_id]
            node_bucket["requests"] += row.requests_count or 0
            node_bucket["margin"] += float(row.actual_margin_brl or 0)
            node_bucket["fallbacks"] += row.fallback_count or 0
            node_bucket["blocks"] += row.block_count or 0
            node_bucket["errors"] += row.error_count or 0
            node_bucket["last_bucket"] = (
                max(node_bucket["last_bucket"], row.bucket_start)
                if node_bucket["last_bucket"]
                else row.bucket_start
            )

        if row.provider:
            prov_bucket = provider_stats[row.provider]
            prov_bucket["requests"] += row.requests_count or 0
            prov_bucket["margin"] += float(row.actual_margin_brl or 0)
            prov_bucket["cost"] += float(row.actual_cost_brl or 0)

        aggregate_rows.append(
            {
                "bucket_start": row.bucket_start.isoformat(),
                "bucket_minutes": row.bucket_minutes,
                "node_id": row.node_id,
                "provider": row.provider,
                "model": row.model,
                "client_id": row.client_id,
                "requests_count": row.requests_count,
                "fallback_count": row.fallback_count,
                "block_count": row.block_count,
                "estimated_revenue_brl": round(float(row.estimated_revenue_brl or 0), 4),
                "estimated_cost_brl": round(float(row.estimated_cost_brl or 0), 4),
                "actual_revenue_brl": round(float(row.actual_revenue_brl or 0), 4),
                "actual_cost_brl": round(float(row.actual_cost_brl or 0), 4),
                "actual_margin_brl": round(float(row.actual_margin_brl or 0), 4),
                "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
                "error_count": row.error_count,
            }
        )

    overview["avg_latency_ms"] = round(
        (overview["avg_latency_ms"] / latency_weight) if latency_weight else 0, 2
    )
    overview["estimated_vs_actual_drift_brl"] = round(drift_abs, 4)
    overview["nodes"] = [
        {
            "node_id": node_id,
            "requests_count": values["requests"],
            "actual_margin_brl": round(values["margin"], 4),
            "fallback_count": values["fallbacks"],
            "block_count": values["blocks"],
            "error_count": values["errors"],
            "last_bucket": values["last_bucket"].isoformat() if values["last_bucket"] else None,
        }
        for node_id, values in sorted(node_stats.items())
    ]
    overview["providers"] = [
        {
            "provider": provider,
            "requests_count": values["requests"],
            "actual_margin_brl": round(values["margin"], 4),
            "actual_cost_brl": round(values["cost"], 4),
        }
        for provider, values in sorted(provider_stats.items())
    ]
    overview["aggregates"] = aggregate_rows
    if health["counts"]["offline"] > 0:
        overview["anomalies"].append(
            {
                "type": "offline_nodes",
                "count": health["counts"]["offline"],
                "message": f"{health['counts']['offline']} node(s) offline",
            }
        )
    if overview["error_count"] > 0 and overview["requests_count"] > 0:
        error_rate = overview["error_count"] / overview["requests_count"]
        if error_rate >= 0.05:
            overview["anomalies"].append(
                {
                    "type": "elevated_error_rate",
                    "count": overview["error_count"],
                    "message": f"error rate {round(error_rate * 100, 2)}%",
                }
            )
    return sanitize_report_payload(overview)


async def list_aggregates(
    db: AsyncSession,
    *,
    hours: int = 24,
    node_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    client_id: str | None = None,
) -> list[dict[str, Any]]:
    since = utc_now() - timedelta(hours=hours)
    stmt = select(CommercialClusterAggregate).where(
        CommercialClusterAggregate.bucket_start >= since
    )
    if node_id:
        stmt = stmt.where(CommercialClusterAggregate.node_id == node_id)
    if provider:
        stmt = stmt.where(CommercialClusterAggregate.provider == provider)
    if model:
        stmt = stmt.where(CommercialClusterAggregate.model == model)
    if client_id:
        stmt = stmt.where(CommercialClusterAggregate.client_id == client_id)
    stmt = stmt.order_by(CommercialClusterAggregate.bucket_start.desc())
    result = await db.execute(stmt)
    return [
        {
            "id": str(row.id),
            "bucket_start": row.bucket_start.isoformat(),
            "bucket_minutes": row.bucket_minutes,
            "node_id": row.node_id,
            "provider": row.provider,
            "model": row.model,
            "client_id": row.client_id,
            "requests_count": row.requests_count,
            "fallback_count": row.fallback_count,
            "block_count": row.block_count,
            "estimated_revenue_brl": round(float(row.estimated_revenue_brl or 0), 4),
            "estimated_cost_brl": round(float(row.estimated_cost_brl or 0), 4),
            "actual_revenue_brl": round(float(row.actual_revenue_brl or 0), 4),
            "actual_cost_brl": round(float(row.actual_cost_brl or 0), 4),
            "actual_margin_brl": round(float(row.actual_margin_brl or 0), 4),
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 2),
            "error_count": row.error_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in result.scalars().all()
    ]


async def export_cluster_payload(
    db: AsyncSession,
    *,
    hours: int = 24,
    settings: Settings | None = None,
) -> dict[str, Any]:
    overview = await get_cluster_overview(db, hours=hours, settings=settings)
    return sanitize_report_payload(
        {
            "cluster_overview": overview,
            "nodes": overview.get("health", {}).get("nodes", []),
            "aggregates": overview.get("aggregates", []),
            "anomalies_cross_node": overview.get("anomalies", []),
        }
    )


def export_cluster_json(report: dict[str, Any]) -> bytes:
    return json.dumps(report, ensure_ascii=True, indent=2).encode("utf-8")


def export_cluster_csv(report: dict[str, Any]) -> str:
    rows = report.get("aggregates", [])
    output = io.StringIO()
    fieldnames = (
        list(rows[0].keys()) if rows else ["bucket_start", "node_id", "provider", "requests_count"]
    )
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def export_cluster_html(report: dict[str, Any]) -> str:
    overview = report.get("cluster_overview", {})
    nodes = report.get("nodes", [])
    aggregates = report.get("aggregates", [])
    anomalies = report.get("anomalies_cross_node", [])

    def _rows(items: list[dict[str, Any]], fields: list[str]) -> str:
        if not items:
            return "<p>No data.</p>"
        header = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
        body = []
        for item in items[:50]:
            body.append(
                "<tr>"
                + "".join(f"<td>{html.escape(str(item.get(field, '-')))}</td>" for field in fields)
                + "</tr>"
            )
        return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Commercial Cluster Analytics</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; color: #111827; }}
      table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
      th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 12px; }}
      th {{ background: #f3f4f6; }}
      .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }}
      .card {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; background: #fff; }}
      .label {{ color: #6b7280; font-size: 12px; }}
      .value {{ font-size: 20px; font-weight: bold; }}
    </style>
  </head>
  <body>
    <h1>Commercial Cluster Analytics</h1>
    <div class="stats">
      <div class="card"><div class="label">Cluster</div><div class="value">{html.escape(str(overview.get("cluster_id", "-")))}</div></div>
      <div class="card"><div class="label">Requests</div><div class="value">{overview.get("requests_count", 0)}</div></div>
      <div class="card"><div class="label">Margin (BRL)</div><div class="value">{overview.get("actual_margin_brl", 0)}</div></div>
      <div class="card"><div class="label">Healthy Nodes</div><div class="value">{overview.get("health", {}).get("counts", {}).get("healthy", 0)}</div></div>
    </div>
    <h2>Nodes</h2>
    {_rows(nodes, ["node_id", "node_role", "status", "last_seen_at"])}
    <h2>Aggregates</h2>
    {_rows(aggregates, ["bucket_start", "node_id", "provider", "model", "requests_count", "actual_margin_brl"])}
    <h2>Anomalies</h2>
    {_rows(anomalies, ["type", "count", "message"])}
  </body>
</html>"""
