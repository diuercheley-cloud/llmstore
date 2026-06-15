# Owner: commercial-ops
from app.api.dependencies import require_admin
from app.core.config import get_settings
from app.models.commercial.commercial_cluster_registry import CommercialClusterRegistry
from app.services.routing.commercial_geo_router import CommercialGeoRouter
from app.services.runtime_dependencies import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    settings = get_settings()
    router_svc = CommercialGeoRouter()

    local_id = settings.commercial_cluster_id
    res = await db.execute(select(CommercialClusterRegistry))
    all_clusters = list(res.scalars().all())

    local_cluster = next((c for c in all_clusters if c.cluster_id == local_id), None)
    if not local_cluster:
        return {"status": "error", "message": "Local cluster not found in registry"}

    candidates_info = [
        {"cluster": c, "margin": 30.0, "health": 1.0} for c in all_clusters if c.status == "active"
    ]

    ranked = router_svc.rank_geo_clusters(local_cluster, candidates_info)

    return {
        "status": "success",
        "enabled": settings.commercial_geo_routing_enabled,
        "mode": settings.commercial_geo_routing_mode,
        "local_cluster": local_id,
        "ranked_clusters": [
            {
                "cluster_id": r["cluster"].cluster_id,
                "score": r["score"],
                "distance_km": r.get("distance_km"),
                "is_cross_ocean": r.get("is_cross_ocean", False),
                "reason": r.get("reason"),
            }
            for r in ranked
        ],
    }


@router.get("/recommendations")
async def get_recommendations(db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    settings = get_settings()
    router_svc = CommercialGeoRouter()

    local_id = settings.commercial_cluster_id
    res = await db.execute(select(CommercialClusterRegistry))
    all_clusters = list(res.scalars().all())

    local_cluster = next((c for c in all_clusters if c.cluster_id == local_id), None)
    if not local_cluster:
        return {"status": "error", "message": "Local cluster not found in registry"}

    candidates_info = [
        {"cluster": c, "margin": 30.0, "health": 1.0} for c in all_clusters if c.status == "active"
    ]
    ranked = router_svc.rank_geo_clusters(local_cluster, candidates_info)

    explanation = router_svc.explain_geo_selection(ranked)

    return {"status": "success", "recommendation": explanation}


@router.post("/simulate")
async def simulate_geo_routing(
    payload: dict, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)
):
    # Payload can contain custom lat/lon for source
    router_svc = CommercialGeoRouter()

    res = await db.execute(select(CommercialClusterRegistry))
    all_clusters = list(res.scalars().all())

    source = CommercialClusterRegistry(
        cluster_id="simulate-source",
        latitude=payload.get("latitude", 0.0),
        longitude=payload.get("longitude", 0.0),
        continent=payload.get("continent", "Unknown"),
    )

    candidates_info = [
        {"cluster": c, "margin": payload.get("margins", {}).get(c.cluster_id, 30.0), "health": 1.0}
        for c in all_clusters
        if c.status == "active"
    ]
    ranked = router_svc.rank_geo_clusters(source, candidates_info)
    explanation = router_svc.explain_geo_selection(ranked)

    return {
        "status": "success",
        "simulation": explanation,
        "ranked": [
            {
                "cluster_id": r["cluster"].cluster_id,
                "score": r["score"],
                "distance_km": r.get("distance_km"),
                "reason": r.get("reason"),
            }
            for r in ranked
        ],
    }
