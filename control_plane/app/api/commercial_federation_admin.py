# Owner: commercial-ops
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.routing.commercial_cluster_registry import list_clusters, register_cluster
from app.services.routing.commercial_federation import (
    cleanup_federated_retention,
    compare_clusters,
    export_federated_csv,
    export_federated_html,
    export_federated_payload,
    ingest_federated_aggregates,
    summarize_federated_overview,
    sync_federation_clusters,
)

router = APIRouter(prefix="/admin/routing/federation", tags=["Commercial Federation"])


def _require_federation_token(x_federation_token: str | None) -> None:
    settings = get_settings()
    if not settings.commercial_federation_require_token:
        return
    expected = settings.commercial_federation_shared_token or ""
    if not expected or x_federation_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid federation token")


@router.get("/clusters", dependencies=[Depends(require_admin)])
async def get_federation_clusters(db: AsyncSession = Depends(get_db_session)):
    rows = await list_clusters(db)
    await db.commit()
    return {"clusters": rows}


@router.post("/clusters", dependencies=[Depends(require_admin)])
async def post_federation_clusters(
    payload: dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db_session),
):
    row = await register_cluster(
        db,
        cluster_id=payload["cluster_id"],
        name=payload.get("name"),
        region=payload.get("region"),
        environment=payload.get("environment"),
        status=payload.get("status", "active"),
        base_url=payload.get("base_url"),
        priority=payload.get("priority", 100),
        tenant_scope_json=payload.get("tenant_scope_json"),
        metadata_json=payload.get("metadata_json"),
    )
    await db.commit()
    return {
        "cluster": {
            "cluster_id": row.cluster_id,
            "name": row.name,
            "region": row.region,
            "environment": row.environment,
            "status": row.status,
            "base_url": row.base_url,
            "priority": row.priority,
            "tenant_scope_json": row.tenant_scope_json or {},
            "metadata_json": row.metadata_json or {},
        }
    }


@router.get("/overview", dependencies=[Depends(require_admin)])
async def get_federation_overview(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db_session),
):
    payload = await summarize_federated_overview(db, hours=hours)
    await db.commit()
    return payload


@router.get("/compare", dependencies=[Depends(require_admin)])
async def get_federation_compare(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db_session),
):
    payload = await compare_clusters(db, hours=hours)
    await db.commit()
    return payload


@router.get("/export", dependencies=[Depends(require_admin)])
async def get_federation_export(
    format: str = Query(default="json", pattern="^(json|csv|html)$"),
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db_session),
):
    payload = await export_federated_payload(db, hours=hours)
    await db.commit()
    if format == "json":
        return JSONResponse(content=payload)
    if format == "csv":
        return Response(content=export_federated_csv(payload), media_type="text/csv")
    return HTMLResponse(content=export_federated_html(payload))


@router.post("/ingest")
async def post_federation_ingest(
    payload: dict[str, Any] = Body(...),
    x_federation_token: str | None = Header(default=None, alias="X-Federation-Token"),
    db: AsyncSession = Depends(get_db_session),
):
    _require_federation_token(x_federation_token)
    try:
        result = await ingest_federated_aggregates(db, payload, sync_type="push")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return result


@router.post("/sync/manual", dependencies=[Depends(require_admin)])
async def post_federation_sync_manual(
    payload: dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db_session),
):
    result = await sync_federation_clusters(db, sync_type=payload.get("sync_type", "manual"))
    await db.commit()
    return result


@router.post("/cleanup", dependencies=[Depends(require_admin)])
async def post_federation_cleanup(db: AsyncSession = Depends(get_db_session)):
    result = await cleanup_federated_retention(db)
    await db.commit()
    return result
