from __future__ import annotations

import hashlib
import logging
import os
import socket
import uuid
from typing import Any

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models.commercial.commercial_node_heartbeat import CommercialNodeHeartbeat
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=utc_now().tzinfo)
    return value.astimezone(utc_now().tzinfo)


def resolve_node_identity(settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    hostname = socket.gethostname()
    process_id = os.getpid()
    role = (cfg.node_role or "unknown").strip() or "unknown"
    raw_node_id = (cfg.node_id or "").strip()
    if raw_node_id:
        node_id = raw_node_id
    else:
        digest = hashlib.sha256(f"{hostname}:{role}:{process_id}".encode()).hexdigest()[:24]
        node_id = f"{role}-{digest}"
    return {
        "node_id": node_id,
        "node_role": role,
        "cluster_id": cfg.cluster_id,
        "hostname": hostname,
        "app_version": cfg.project_version,
        "process_id": process_id,
        "started_at": utc_now(),
        "metadata_json": sanitize_report_payload(
            {
                "cluster_id": cfg.cluster_id,
                "hostname": hostname,
                "node_role": role,
                "process_id": process_id,
            }
        ),
    }


def _derive_status(last_seen_at, settings: Settings) -> str:
    now = utc_now()
    normalized = _as_utc(last_seen_at)
    delta = (now - normalized).total_seconds()
    if delta >= settings.commercial_node_offline_after_seconds:
        return "offline"
    if delta >= max(1, settings.commercial_node_heartbeat_interval_seconds * 2):
        return "degraded"
    return "healthy"


async def write_heartbeat(
    db: AsyncSession,
    node_identity: dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    identity = node_identity or resolve_node_identity(cfg)
    stmt = select(CommercialNodeHeartbeat).where(
        CommercialNodeHeartbeat.node_id == identity["node_id"]
    )
    result = await db.execute(stmt)
    heartbeat = result.scalar_one_or_none()
    now = utc_now()
    if heartbeat is None:
        heartbeat = CommercialNodeHeartbeat(
            id=uuid.uuid4(),
            node_id=identity["node_id"],
            node_role=identity["node_role"],
            hostname=identity.get("hostname"),
            app_version=identity.get("app_version"),
            process_id=identity.get("process_id"),
            started_at=identity.get("started_at") or now,
            last_seen_at=now,
            status="healthy",
            metadata_json=identity.get("metadata_json"),
        )
        db.add(heartbeat)
    else:
        heartbeat.node_role = identity["node_role"]
        heartbeat.hostname = identity.get("hostname")
        heartbeat.app_version = identity.get("app_version")
        heartbeat.process_id = identity.get("process_id")
        heartbeat.last_seen_at = now
        heartbeat.status = "healthy"
        heartbeat.metadata_json = identity.get("metadata_json")
    await db.flush()
    return {
        "node_id": heartbeat.node_id,
        "status": heartbeat.status,
        "last_seen_at": heartbeat.last_seen_at.isoformat(),
    }


async def mark_stale_nodes_offline(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> int:
    cfg = settings or get_settings()
    result = await db.execute(select(CommercialNodeHeartbeat))
    updated = 0
    for row in result.scalars().all():
        next_status = _derive_status(row.last_seen_at, cfg)
        if row.status != next_status:
            row.status = next_status
            updated += 1
    await db.flush()
    return updated


async def list_nodes(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    cfg = settings or get_settings()
    result = await db.execute(
        select(CommercialNodeHeartbeat).order_by(
            CommercialNodeHeartbeat.node_role.asc(), CommercialNodeHeartbeat.node_id.asc()
        )
    )
    nodes = []
    for row in result.scalars().all():
        status = _derive_status(row.last_seen_at, cfg)
        if row.status != status:
            row.status = status
        nodes.append(
            {
                "id": str(row.id),
                "node_id": row.node_id,
                "node_role": row.node_role,
                "hostname": row.hostname,
                "app_version": row.app_version,
                "process_id": row.process_id,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "last_seen_at": _as_utc(row.last_seen_at).isoformat() if row.last_seen_at else None,
                "status": status,
                "metadata_json": row.metadata_json or {},
            }
        )
    await db.flush()
    return nodes


async def summarize_cluster_health(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    nodes = await list_nodes(db, settings=cfg)
    counts = {"healthy": 0, "degraded": 0, "offline": 0}
    for node in nodes:
        counts[node["status"]] = counts.get(node["status"], 0) + 1
    cluster_status = "healthy"
    if counts["offline"] > 0:
        cluster_status = "degraded"
    if nodes and counts["offline"] == len(nodes):
        cluster_status = "offline"
    return {
        "cluster_id": cfg.cluster_id,
        "node_id": resolve_node_identity(cfg)["node_id"],
        "status": cluster_status,
        "counts": counts,
        "total_nodes": len(nodes),
        "offline_after_seconds": cfg.commercial_node_offline_after_seconds,
        "heartbeat_interval_seconds": cfg.commercial_node_heartbeat_interval_seconds,
        "nodes": nodes,
    }


async def commercial_distributed_analytics_loop(stop_event) -> None:
    cfg = get_settings()
    if not cfg.commercial_distributed_analytics_enabled:
        return
    from app.services.routing.commercial_cluster_aggregates import (
        aggregate_recent,
        cleanup_old_analytics,
    )
    from app.services.routing.commercial_event_ingest import process_pending_events
    from app.services.routing.commercial_leader_election import (
        renew_leader_lease,
        try_acquire_leader,
    )

    identity = resolve_node_identity(cfg)
    tick = 0
    current_lease_token: int | None = None
    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                await write_heartbeat(session, identity, settings=cfg)
                await mark_stale_nodes_offline(session, settings=cfg)
                await process_pending_events(session, settings=cfg)
                lease = await try_acquire_leader(
                    session,
                    cluster_id=cfg.cluster_id,
                    leader_role="aggregator",
                    node_id=identity["node_id"],
                    metadata_json={"job": "distributed_analytics_loop"},
                    settings=cfg,
                )
                if lease.get("acquired"):
                    current_lease_token = int(lease["lease"]["lease_token"])
                    renewed = await renew_leader_lease(
                        session,
                        cluster_id=cfg.cluster_id,
                        leader_role="aggregator",
                        node_id=identity["node_id"],
                        lease_token=current_lease_token,
                        metadata_json={"job": "distributed_analytics_loop", "tick": tick},
                        settings=cfg,
                    )
                    if renewed.get("renewed"):
                        if (
                            tick
                            % max(1, 300 // max(1, cfg.commercial_node_heartbeat_interval_seconds))
                            == 0
                        ):
                            await aggregate_recent(session, hours=1, settings=cfg)
                        if (
                            tick
                            % max(1, 3600 // max(1, cfg.commercial_node_heartbeat_interval_seconds))
                            == 0
                        ):
                            await cleanup_old_analytics(
                                session,
                                settings=cfg,
                                lease_token=current_lease_token,
                                cluster_id=cfg.cluster_id,
                                node_id=identity["node_id"],
                            )
                    else:
                        current_lease_token = None
                await session.commit()
        except Exception as exc:
            logger.warning("Distributed commercial analytics loop failure: %s", exc)
        tick += 1
        try:
            import asyncio

            await asyncio.wait_for(
                stop_event.wait(), timeout=cfg.commercial_node_heartbeat_interval_seconds
            )
        except Exception:
            continue
