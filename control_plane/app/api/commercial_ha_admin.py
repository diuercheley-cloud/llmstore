# Owner: commercial-ops
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.admin_action_log import AdminActionLog
from app.models.commercial_leader_lease import CommercialLeaderLease
from app.services.auth import require_admin
from app.services.routing.commercial_leader_election import (
    force_expire_stale_leases,
    get_current_leader,
    release_leader,
    try_acquire_leader,
)
from app.services.routing.commercial_node_heartbeat import list_nodes, resolve_node_identity

router = APIRouter(
    prefix="/admin/routing/ha",
    tags=["Commercial HA"],
    dependencies=[Depends(require_admin)],
)


async def _recent_failovers(db: AsyncSession, limit: int = 20) -> list[dict[str, Any]]:
    result = await db.execute(
        select(AdminActionLog)
        .where(
            AdminActionLog.action.in_(
                [
                    "failover_promoted",
                    "leader_expired",
                    "scheduler_stopped_due_lease_loss",
                    "fencing_rejected",
                ]
            )
        )
        .order_by(desc(AdminActionLog.created_at))
        .limit(limit)
    )
    return [
        {
            "action": row.action,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "payload_json": row.payload_json or {},
        }
        for row in result.scalars().all()
    ]


@router.get("/leaders")
async def get_ha_leaders(db: AsyncSession = Depends(get_db_session)):
    identity = resolve_node_identity()
    roles = ["scheduler", "aggregator", "reporter", "calibration", "canary", "global"]
    leaders = []
    for role in roles:
        leaders.append(await get_current_leader(db, cluster_id=identity["cluster_id"], leader_role=role))
    await db.commit()
    return {
        "cluster_id": identity["cluster_id"],
        "node_id": identity["node_id"],
        "leaders": [leader for leader in leaders if leader],
    }


@router.get("/cluster-state")
async def get_ha_cluster_state(db: AsyncSession = Depends(get_db_session)):
    identity = resolve_node_identity()
    expire_result = await force_expire_stale_leases(db, cluster_id=identity["cluster_id"])
    leaders = []
    for role in ["scheduler", "aggregator", "reporter", "calibration", "canary", "global"]:
        leaders.append(await get_current_leader(db, cluster_id=identity["cluster_id"], leader_role=role))
    stale_result = await db.execute(
        select(CommercialLeaderLease)
        .where(
            CommercialLeaderLease.cluster_id == identity["cluster_id"],
            CommercialLeaderLease.status == "expired",
        )
        .order_by(desc(CommercialLeaderLease.last_heartbeat_at))
        .limit(20)
    )
    stale = [
        {
            "node_id": row.node_id,
            "leader_role": row.leader_role,
            "lease_token": int(row.lease_token),
            "lease_expires_at": row.lease_expires_at.isoformat() if row.lease_expires_at else None,
            "status": row.status,
        }
        for row in stale_result.scalars().all()
    ]
    payload = {
        "cluster_id": identity["cluster_id"],
        "node_id": identity["node_id"],
        "leaders": [leader for leader in leaders if leader],
        "nodes": await list_nodes(db),
        "stale_leaders": stale,
        "failovers_recent": await _recent_failovers(db),
        "expired_now": expire_result,
    }
    await db.commit()
    return payload


@router.post("/force-expire")
async def post_force_expire_ha(
    payload: dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db_session),
):
    identity = resolve_node_identity()
    result = await force_expire_stale_leases(
        db,
        cluster_id=payload.get("cluster_id") or identity["cluster_id"],
        leader_role=payload.get("leader_role"),
    )
    await db.commit()
    return result


@router.post("/release")
async def post_release_ha(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    identity = resolve_node_identity()
    result = await release_leader(
        db,
        cluster_id=payload.get("cluster_id") or identity["cluster_id"],
        leader_role=payload["leader_role"],
        node_id=payload.get("node_id") or identity["node_id"],
        lease_token=payload.get("lease_token"),
    )
    await db.commit()
    return result


@router.post("/acquire")
async def post_acquire_ha(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    identity = resolve_node_identity()
    result = await try_acquire_leader(
        db,
        cluster_id=payload.get("cluster_id") or identity["cluster_id"],
        leader_role=payload["leader_role"],
        node_id=payload.get("node_id") or identity["node_id"],
        metadata_json=payload.get("metadata_json") or {},
    )
    await db.commit()
    return result
