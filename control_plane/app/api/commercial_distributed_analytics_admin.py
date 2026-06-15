# Owner: commercial-ops
from __future__ import annotations

from typing import Any

from app.services.auth import require_admin
from app.services.routing.commercial_cluster_aggregates import (
    cleanup_old_analytics,
    export_cluster_csv,
    export_cluster_html,
    export_cluster_payload,
    get_cluster_overview,
    list_aggregates,
    rebuild_aggregates,
)
from app.services.routing.commercial_event_ingest import (
    ingest_routing_event,
    process_pending_events,
)
from app.services.routing.commercial_leader_election import try_acquire_leader
from app.services.routing.commercial_node_heartbeat import (
    list_nodes,
    mark_stale_nodes_offline,
    resolve_node_identity,
)
from app.services.runtime_dependencies import get_db_session
from fastapi import APIRouter, Body, Depends, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin/routing/distributed",
    tags=["Commercial Distributed Analytics"],
    dependencies=[Depends(require_admin)],
)


@router.get("/nodes")
async def get_distributed_nodes(
    db: AsyncSession = Depends(get_db_session),
):
    await mark_stale_nodes_offline(db)
    await db.commit()
    return {
        "cluster_id": resolve_node_identity()["cluster_id"],
        "nodes": await list_nodes(db),
    }


@router.get("/cluster-overview")
async def get_distributed_cluster_overview(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db_session),
):
    payload = await get_cluster_overview(db, hours=hours)
    await db.commit()
    return payload


@router.get("/aggregates")
async def get_distributed_aggregates(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    node_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await list_aggregates(
        db,
        hours=hours,
        node_id=node_id,
        provider=provider,
        model=model,
        client_id=client_id,
    )
    return {"aggregates": rows}


@router.post("/ingest")
async def post_distributed_ingest(
    payload: dict[str, Any] = Body(...),
    node_id: str | None = Query(default=None),
    process_now: bool = Query(default=False),
    db: AsyncSession = Depends(get_db_session),
):
    identity = resolve_node_identity()
    result = await ingest_routing_event(db, payload, node_id or identity["node_id"])
    processing = None
    if process_now and result.get("accepted"):
        processing = await process_pending_events(db)
    await db.commit()
    return {"ingest": result, "processing": processing}


@router.post("/rebuild-aggregates")
async def post_rebuild_distributed_aggregates(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db_session),
):
    identity = resolve_node_identity()
    lease = await try_acquire_leader(
        db,
        cluster_id=identity["cluster_id"],
        leader_role="aggregator",
        node_id=identity["node_id"],
        metadata_json={"job": "admin_rebuild_aggregates"},
    )
    if not lease.get("acquired"):
        await db.commit()
        return {"executed": False, "reason": "not_leader", "leader": lease.get("lease")}
    result = await rebuild_aggregates(
        db,
        hours=hours,
        lease_token=int(lease["lease"]["lease_token"]),
        cluster_id=identity["cluster_id"],
        node_id=identity["node_id"],
    )
    await db.commit()
    return result


@router.post("/cleanup")
async def post_cleanup_distributed_analytics(
    db: AsyncSession = Depends(get_db_session),
):
    identity = resolve_node_identity()
    lease = await try_acquire_leader(
        db,
        cluster_id=identity["cluster_id"],
        leader_role="aggregator",
        node_id=identity["node_id"],
        metadata_json={"job": "admin_cleanup_analytics"},
    )
    if not lease.get("acquired"):
        await db.commit()
        return {"executed": False, "reason": "not_leader", "leader": lease.get("lease")}
    result = await cleanup_old_analytics(
        db,
        lease_token=int(lease["lease"]["lease_token"]),
        cluster_id=identity["cluster_id"],
        node_id=identity["node_id"],
    )
    await db.commit()
    return result


@router.get("/export")
async def get_distributed_export(
    format: str = Query(default="json", pattern="^(json|csv|html)$"),
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db_session),
):
    report = await export_cluster_payload(db, hours=hours)
    await db.commit()
    if format == "json":
        return JSONResponse(content=report)
    if format == "csv":
        return Response(content=export_cluster_csv(report), media_type="text/csv")
    return HTMLResponse(content=export_cluster_html(report))
