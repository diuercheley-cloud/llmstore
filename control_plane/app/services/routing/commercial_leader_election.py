from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.admin_action_log import AdminActionLog
from app.models.commercial_leader_lease import CommercialLeaderLease
from app.models.commercial_node_heartbeat import CommercialNodeHeartbeat
from app.services.routing.commercial_node_heartbeat import _derive_status
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

LEADER_ROLES = {"scheduler", "aggregator", "reporter", "calibration", "canary", "global"}
LEASE_ACTIVE = "active"
LEASE_EXPIRED = "expired"
LEASE_RELEASED = "released"


def _now():
    return utc_now()


def _as_utc(value):
    if value is None:
        return None
    now = _now()
    if value.tzinfo is None:
        return value.replace(tzinfo=now.tzinfo)
    return value.astimezone(now.tzinfo)


def _normalize_role(leader_role: str) -> str:
    role = (leader_role or "global").strip().lower()
    if role not in LEADER_ROLES:
        raise ValueError(f"unsupported leader role: {leader_role}")
    return role


def _sanitize_metadata(metadata_json: dict[str, Any] | None) -> dict[str, Any]:
    return sanitize_report_payload(metadata_json or {})


def _serialize_lease(lease: CommercialLeaderLease | None, *, settings: Settings | None = None) -> dict[str, Any] | None:
    if lease is None:
        return None
    cfg = settings or get_settings()
    now = _now()
    lease_expires_at = _as_utc(lease.lease_expires_at)
    last_heartbeat_at = _as_utc(lease.last_heartbeat_at)
    lease_acquired_at = _as_utc(lease.lease_acquired_at)
    expires_in = (lease_expires_at - now).total_seconds() if lease_expires_at else None
    heartbeat_age = (now - last_heartbeat_at).total_seconds() if last_heartbeat_at else None
    return {
        "id": str(lease.id),
        "cluster_id": lease.cluster_id,
        "leader_role": lease.leader_role,
        "node_id": lease.node_id,
        "lease_token": int(lease.lease_token),
        "lease_acquired_at": lease_acquired_at.isoformat() if lease_acquired_at else None,
        "lease_expires_at": lease_expires_at.isoformat() if lease_expires_at else None,
        "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
        "status": lease.status,
        "metadata_json": lease.metadata_json or {},
        "heartbeat_age_seconds": round(float(heartbeat_age or 0), 3),
        "lease_expires_in_seconds": round(float(expires_in or 0), 3),
        "is_expired": bool(lease_expires_at and lease_expires_at <= now),
        "fencing_enabled": cfg.commercial_leader_fencing_enabled,
    }


async def _log_audit(
    db: AsyncSession,
    *,
    action: str,
    status: str = "success",
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        AdminActionLog(
            action=action,
            admin_role="system",
            status=status,
            payload_json=_sanitize_metadata(payload),
        )
    )
    await db.flush()


async def _active_lease_query(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
) -> CommercialLeaderLease | None:
    result = await db.execute(
        select(CommercialLeaderLease)
        .where(
            CommercialLeaderLease.cluster_id == cluster_id,
            CommercialLeaderLease.leader_role == leader_role,
            CommercialLeaderLease.status == LEASE_ACTIVE,
        )
        .order_by(CommercialLeaderLease.lease_acquired_at.desc())
    )
    return result.scalars().first()


async def _max_lease_token(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
) -> int:
    result = await db.execute(
        select(func.max(CommercialLeaderLease.lease_token)).where(
            CommercialLeaderLease.cluster_id == cluster_id,
            CommercialLeaderLease.leader_role == leader_role,
        )
    )
    return int(result.scalar() or 0)


async def force_expire_stale_leases(
    db: AsyncSession,
    *,
    cluster_id: str | None = None,
    leader_role: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    now = _now()
    role = _normalize_role(leader_role) if leader_role else None
    stmt = select(CommercialLeaderLease).where(CommercialLeaderLease.status == LEASE_ACTIVE)
    if cluster_id:
        stmt = stmt.where(CommercialLeaderLease.cluster_id == cluster_id)
    if role:
        stmt = stmt.where(CommercialLeaderLease.leader_role == role)
    leases = list((await db.execute(stmt)).scalars().all())
    node_ids = {lease.node_id for lease in leases}
    heartbeats = {}
    if node_ids:
        hb_result = await db.execute(
            select(CommercialNodeHeartbeat).where(CommercialNodeHeartbeat.node_id.in_(node_ids))
        )
        heartbeats = {row.node_id: row for row in hb_result.scalars().all()}
    expired: list[dict[str, Any]] = []
    skew_window = timedelta(seconds=cfg.commercial_lease_max_clock_skew_seconds)
    for lease in leases:
        heartbeat = heartbeats.get(lease.node_id)
        heartbeat_status = _derive_status(heartbeat.last_seen_at, cfg) if heartbeat else "unknown"
        stale = _as_utc(lease.lease_expires_at) <= (now - skew_window) or (heartbeat is not None and heartbeat_status == "offline")
        if not stale:
            continue
        lease.status = LEASE_EXPIRED
        expired.append(
            {
                "cluster_id": lease.cluster_id,
                "leader_role": lease.leader_role,
                "node_id": lease.node_id,
                "lease_token": int(lease.lease_token),
                "heartbeat_status": heartbeat_status,
            }
        )
        await _log_audit(
            db,
            action="leader_expired",
            payload={
                "cluster_id": lease.cluster_id,
                "leader_role": lease.leader_role,
                "node_id": lease.node_id,
                "lease_token": int(lease.lease_token),
                "heartbeat_status": heartbeat_status,
            },
        )
    await db.flush()
    return {"expired_count": len(expired), "expired": expired}


async def get_current_leader(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    cfg = settings or get_settings()
    role = _normalize_role(leader_role)
    if not cfg.commercial_leader_election_enabled:
        return {
            "cluster_id": cluster_id,
            "leader_role": role,
            "node_id": "election-disabled",
            "lease_token": 0,
            "status": LEASE_ACTIVE,
            "metadata_json": {"mode": "single-node-compatible"},
        }
    await force_expire_stale_leases(db, cluster_id=cluster_id, leader_role=role, settings=cfg)
    lease = await _active_lease_query(db, cluster_id=cluster_id, leader_role=role)
    if lease is None or _as_utc(lease.lease_expires_at) <= _now():
        return None
    return _serialize_lease(lease, settings=cfg)


async def try_acquire_leader(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
    node_id: str,
    metadata_json: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    role = _normalize_role(leader_role)
    sanitized_metadata = _sanitize_metadata(metadata_json)
    if not cfg.commercial_leader_election_enabled:
        return {
            "acquired": True,
            "lease": {
                "cluster_id": cluster_id,
                "leader_role": role,
                "node_id": node_id,
                "lease_token": 0,
                "status": LEASE_ACTIVE,
                "metadata_json": sanitized_metadata,
            },
            "reason": "leader_election_disabled",
        }
    expire_result = await force_expire_stale_leases(db, cluster_id=cluster_id, leader_role=role, settings=cfg)
    current = await _active_lease_query(db, cluster_id=cluster_id, leader_role=role)
    if current and current.node_id == node_id and _as_utc(current.lease_expires_at) > _now():
        renewed = await renew_leader_lease(
            db,
            cluster_id=cluster_id,
            leader_role=role,
            node_id=node_id,
            lease_token=int(current.lease_token),
            metadata_json=sanitized_metadata,
            settings=cfg,
        )
        return {"acquired": True, "lease": renewed["lease"], "reason": "already_leader"}
    if current and _as_utc(current.lease_expires_at) > _now():
        return {
            "acquired": False,
            "lease": _serialize_lease(current, settings=cfg),
            "reason": "leader_exists",
        }
    next_token = await _max_lease_token(db, cluster_id=cluster_id, leader_role=role) + 1
    now = _now()
    lease = CommercialLeaderLease(
        id=uuid.uuid4(),
        cluster_id=cluster_id,
        leader_role=role,
        node_id=node_id,
        lease_token=next_token,
        lease_acquired_at=now,
        lease_expires_at=now + timedelta(seconds=cfg.commercial_lease_duration_seconds),
        last_heartbeat_at=now,
        status=LEASE_ACTIVE,
        metadata_json=sanitized_metadata,
    )
    db.add(lease)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info("leader lease acquire conflict", extra={"extra_data": {"cluster_id": cluster_id, "leader_role": role}})
        fresh = await get_current_leader(db, cluster_id=cluster_id, leader_role=role, settings=cfg)
        return {"acquired": False, "lease": fresh, "reason": "integrity_conflict"}
    action = "failover_promoted" if expire_result["expired_count"] else "leader_acquired"
    await _log_audit(
        db,
        action=action,
        payload={
            "cluster_id": cluster_id,
            "leader_role": role,
            "node_id": node_id,
            "lease_token": next_token,
            "metadata_json": sanitized_metadata,
        },
    )
    return {"acquired": True, "lease": _serialize_lease(lease, settings=cfg), "reason": action}


async def renew_leader_lease(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
    node_id: str,
    lease_token: int,
    metadata_json: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    role = _normalize_role(leader_role)
    if not cfg.commercial_leader_election_enabled:
        return {
            "renewed": True,
            "lease": {
                "cluster_id": cluster_id,
                "leader_role": role,
                "node_id": node_id,
                "lease_token": lease_token,
                "status": LEASE_ACTIVE,
            },
            "reason": "leader_election_disabled",
        }
    await force_expire_stale_leases(db, cluster_id=cluster_id, leader_role=role, settings=cfg)
    lease = await _active_lease_query(db, cluster_id=cluster_id, leader_role=role)
    if lease is None or lease.node_id != node_id or int(lease.lease_token) != int(lease_token) or _as_utc(lease.lease_expires_at) <= _now():
        await _log_audit(
            db,
            action="scheduler_stopped_due_lease_loss",
            status="rejected",
            payload={
                "cluster_id": cluster_id,
                "leader_role": role,
                "node_id": node_id,
                "lease_token": lease_token,
            },
        )
        return {"renewed": False, "lease": _serialize_lease(lease, settings=cfg) if lease else None, "reason": "lease_lost"}
    now = _now()
    lease.last_heartbeat_at = now
    lease.lease_expires_at = now + timedelta(seconds=cfg.commercial_lease_duration_seconds)
    if metadata_json is not None:
        lease.metadata_json = _sanitize_metadata(metadata_json)
    await db.flush()
    await _log_audit(
        db,
        action="leader_renewed",
        payload={
            "cluster_id": cluster_id,
            "leader_role": role,
            "node_id": node_id,
            "lease_token": int(lease.lease_token),
        },
    )
    return {"renewed": True, "lease": _serialize_lease(lease, settings=cfg), "reason": "renewed"}


async def release_leader(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
    node_id: str,
    lease_token: int | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    role = _normalize_role(leader_role)
    if not cfg.commercial_leader_election_enabled:
        return {"released": True, "reason": "leader_election_disabled"}
    lease = await _active_lease_query(db, cluster_id=cluster_id, leader_role=role)
    if lease is None or lease.node_id != node_id or (lease_token is not None and int(lease.lease_token) != int(lease_token)):
        return {"released": False, "reason": "not_current_leader", "lease": _serialize_lease(lease, settings=cfg) if lease else None}
    lease.status = LEASE_RELEASED
    lease.lease_expires_at = _now()
    lease.last_heartbeat_at = _now()
    await db.flush()
    await _log_audit(
        db,
        action="leader_released",
        payload={
            "cluster_id": cluster_id,
            "leader_role": role,
            "node_id": node_id,
            "lease_token": int(lease.lease_token),
        },
    )
    return {"released": True, "lease": _serialize_lease(lease, settings=cfg), "reason": "released"}


async def validate_fencing_token(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
    lease_token: int,
    node_id: str | None = None,
    settings: Settings | None = None,
) -> bool:
    cfg = settings or get_settings()
    role = _normalize_role(leader_role)
    if not cfg.commercial_leader_election_enabled or not cfg.commercial_leader_fencing_enabled:
        return True
    current = await get_current_leader(db, cluster_id=cluster_id, leader_role=role, settings=cfg)
    valid = bool(
        current
        and int(current["lease_token"]) == int(lease_token)
        and (node_id is None or current["node_id"] == node_id)
        and current.get("status") == LEASE_ACTIVE
    )
    if not valid:
        await _log_audit(
            db,
            action="fencing_rejected",
            status="rejected",
            payload={
                "cluster_id": cluster_id,
                "leader_role": role,
                "node_id": node_id,
                "lease_token": lease_token,
                "current_leader": current,
            },
        )
    return valid


async def is_current_leader(
    db: AsyncSession,
    *,
    cluster_id: str,
    leader_role: str,
    node_id: str,
    lease_token: int | None = None,
    settings: Settings | None = None,
) -> bool:
    current = await get_current_leader(db, cluster_id=cluster_id, leader_role=_normalize_role(leader_role), settings=settings)
    if not current:
        return False
    if current["node_id"] != node_id:
        return False
    if lease_token is not None and int(current["lease_token"]) != int(lease_token):
        return False
    return current.get("status") == LEASE_ACTIVE and not current.get("is_expired", False)
