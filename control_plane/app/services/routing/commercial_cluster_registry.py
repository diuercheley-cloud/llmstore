from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.time import utc_now
from app.models.commercial_cluster_registry import CommercialClusterRegistry
from app.services.routing.commercial_report_export import sanitize_report_payload

VALID_CLUSTER_ENVIRONMENTS = {"local", "staging", "production", "edge"}
VALID_CLUSTER_STATUSES = {"active", "degraded", "offline", "disabled"}


def sanitize_cluster_metadata(payload: Any) -> dict[str, Any]:
    sanitized = sanitize_report_payload(payload or {})
    return sanitized if isinstance(sanitized, dict) else {"value": sanitized}


def _normalize_tenant_scope(scope: Any) -> dict[str, Any]:
    if scope is None:
        return {}
    sanitized = sanitize_report_payload(scope)
    if isinstance(sanitized, list):
        tenants = sorted({str(item).strip() for item in sanitized if str(item).strip()})
        return {"tenants": tenants, "allow_untagged": False}
    if not isinstance(sanitized, dict):
        return {}
    tenants = sanitized.get("tenants")
    if isinstance(tenants, list):
        sanitized["tenants"] = sorted({str(item).strip() for item in tenants if str(item).strip()})
    else:
        sanitized["tenants"] = []
    sanitized["allow_untagged"] = bool(sanitized.get("allow_untagged", False))
    return sanitized


def validate_tenant_scope(
    tenant_scope_json: Any,
    tenant_id: str | None,
    *,
    allow_local: bool = False,
) -> tuple[bool, str | None]:
    if allow_local:
        return True, None
    scope = _normalize_tenant_scope(tenant_scope_json)
    tenant = str(tenant_id).strip() if tenant_id else None
    tenants = set(scope.get("tenants") or [])
    allow_untagged = bool(scope.get("allow_untagged", False))
    if not tenants:
        if tenant is None:
            return True, None
        return False, "tenant out of scope"
    if tenant is None:
        return (allow_untagged, None if allow_untagged else "tenant required by cluster scope")
    if tenant in tenants:
        return True, None
    return False, "tenant out of scope"


async def register_cluster(
    db: AsyncSession,
    *,
    cluster_id: str,
    name: str | None = None,
    region: str | None = None,
    environment: str | None = None,
    status: str = "active",
    base_url: str | None = None,
    priority: int = 100,
    tenant_scope_json: Any = None,
    metadata_json: Any = None,
    last_seen_at=None,
) -> CommercialClusterRegistry:
    normalized_cluster_id = (cluster_id or "").strip() or "local"
    normalized_environment = environment if environment in VALID_CLUSTER_ENVIRONMENTS else "local"
    normalized_status = status if status in VALID_CLUSTER_STATUSES else "active"
    scope = _normalize_tenant_scope(tenant_scope_json)
    metadata = sanitize_cluster_metadata(metadata_json)

    existing = (
        await db.execute(select(CommercialClusterRegistry).where(CommercialClusterRegistry.cluster_id == normalized_cluster_id))
    ).scalar_one_or_none()
    if existing is None:
        existing = CommercialClusterRegistry(
            cluster_id=normalized_cluster_id,
            name=(name or normalized_cluster_id).strip() or normalized_cluster_id,
            region=(region or None),
            environment=normalized_environment,
            status=normalized_status,
            base_url=(base_url or None),
            priority=int(priority),
            tenant_scope_json=scope,
            metadata_json=metadata,
            last_seen_at=last_seen_at,
        )
        db.add(existing)
    else:
        existing.name = (name or existing.name or normalized_cluster_id).strip() or normalized_cluster_id
        existing.region = region if region is not None else existing.region
        existing.environment = normalized_environment
        existing.status = normalized_status
        existing.base_url = base_url if base_url is not None else existing.base_url
        existing.priority = int(priority)
        existing.tenant_scope_json = scope
        existing.metadata_json = metadata
        existing.last_seen_at = last_seen_at if last_seen_at is not None else existing.last_seen_at
        existing.updated_at = utc_now()
    await db.flush()
    return existing


async def ensure_local_cluster_registered(
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> CommercialClusterRegistry:
    cfg = settings or get_settings()
    return await register_cluster(
        db,
        cluster_id=cfg.commercial_cluster_id,
        name=cfg.commercial_cluster_id,
        region=cfg.commercial_cluster_region or None,
        environment=cfg.commercial_cluster_environment,
        status="active",
        base_url=None,
        priority=100,
        tenant_scope_json={"tenants": [], "allow_untagged": True},
        metadata_json={
            "local_cluster": True,
            "federation_enabled": cfg.commercial_federation_enabled,
            "federation_mode": cfg.commercial_federation_mode,
        },
        last_seen_at=utc_now(),
    )


async def update_cluster_status(
    db: AsyncSession,
    *,
    cluster_id: str,
    status: str,
    last_seen_at=None,
    metadata_json: Any = None,
) -> CommercialClusterRegistry | None:
    row = (await db.execute(select(CommercialClusterRegistry).where(CommercialClusterRegistry.cluster_id == cluster_id))).scalar_one_or_none()
    if row is None:
        return None
    row.status = status if status in VALID_CLUSTER_STATUSES else row.status
    row.last_seen_at = last_seen_at if last_seen_at is not None else utc_now()
    if metadata_json is not None:
        row.metadata_json = sanitize_cluster_metadata(metadata_json)
    row.updated_at = utc_now()
    await db.flush()
    return row


async def mark_cluster_offline(db: AsyncSession, *, cluster_id: str) -> CommercialClusterRegistry | None:
    return await update_cluster_status(db, cluster_id=cluster_id, status="offline", last_seen_at=utc_now())


async def list_clusters(
    db: AsyncSession,
    *,
    include_disabled: bool = True,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    await ensure_local_cluster_registered(db, settings=settings)
    stmt = select(CommercialClusterRegistry).order_by(CommercialClusterRegistry.priority.asc(), CommercialClusterRegistry.cluster_id.asc())
    if not include_disabled:
        stmt = stmt.where(CommercialClusterRegistry.status != "disabled")
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": str(row.id),
            "cluster_id": row.cluster_id,
            "name": row.name,
            "region": row.region,
            "environment": row.environment,
            "status": row.status,
            "base_url": row.base_url,
            "priority": row.priority,
            "tenant_scope_json": row.tenant_scope_json or {},
            "metadata_json": row.metadata_json or {},
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]
