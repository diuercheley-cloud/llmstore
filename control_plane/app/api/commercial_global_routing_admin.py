# Owner: commercial-ops
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.routing import commercial_global_router
from app.services.routing.commercial_analytics import audit_log

router = APIRouter()


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    return await commercial_global_router.get_global_router_overview(db)


@router.get("/recommendations")
async def get_recommendations(
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    return await commercial_global_router.generate_cluster_recommendations(db)


@router.post("/simulate")
async def simulate_route(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> dict[str, Any]:
    tenant_id = payload.get("tenant_id")
    provider = payload.get("provider")
    model = payload.get("model")
    region_preference = payload.get("region_preference")
    estimated_tokens = int(payload.get("estimated_tokens") or 0)
    
    result = await commercial_global_router.simulate_global_route(
        db,
        tenant_id=tenant_id,
        provider=provider,
        model=model,
        region_preference=region_preference,
        estimated_tokens=estimated_tokens,
    )
    
    recommended = result.get("recommended_cluster")
    recommended_id = recommended.get("cluster_id") if recommended else None

    # Audit log
    await audit_log(
        db,
        event_type="global_route_simulated",
        client_id="admin",
        details={
            "tenant_id": tenant_id,
            "provider": provider,
            "model": model,
            "region_preference": region_preference,
            "recommended_cluster": recommended_id,
        }
    )
    
    # Register rejections in audit
    for rejected in result.get("rejected_clusters", []):
        await audit_log(
            db,
            event_type="cluster_rejected",
            client_id="admin",
            details={
                "cluster_id": rejected["cluster_id"],
                "reason": rejected["reason"],
                "message": rejected["message"]
            }
        )
        
    return result


@router.get("/export")
async def export_routing(
    format: str = Query("json", pattern="^(json|csv|html)$"),
    db: AsyncSession = Depends(get_db_session),
    _admin: Any = Depends(require_admin),
) -> Any:
    data = await commercial_global_router.get_global_router_overview(db)
    
    if format == "csv":
        content = commercial_global_router.export_routing_csv(data)
        return Response(content=content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=global_routing.csv"})
    
    if format == "html":
        content = commercial_global_router.export_routing_html(data)
        return Response(content=content, media_type="text/html")
        
    return data
