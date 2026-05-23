# Owner: commercial-ops
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.services.auth import require_admin as get_admin_user
from app.db.session import get_db_session as get_db
from app.core.config import get_settings
from app.services.routing.commercial_cross_cluster_forwarder import _circuit_breakers, CommercialCrossClusterForwarder

router = APIRouter()
cfg = get_settings()

@router.get("/status")
async def get_forwarding_status(admin=Depends(get_admin_user)):
    return {
        "enabled": cfg.commercial_cross_cluster_forwarding_enabled,
        "mode": cfg.commercial_cross_cluster_forwarding_mode,
        "circuit_breaker_enabled": cfg.commercial_cross_cluster_forwarding_circuit_breaker_enabled,
        "circuit_breaker_failure_threshold": cfg.commercial_cross_cluster_forwarding_circuit_breaker_failure_threshold,
        "max_shifted_percent": cfg.commercial_cross_cluster_forwarding_max_shifted_percent,
    }

@router.get("/circuit-breakers")
async def get_circuit_breakers(admin=Depends(get_admin_user)):
    return {
        "circuit_breakers": _circuit_breakers
    }

@router.post("/reset-circuit-breaker")
async def reset_circuit_breaker(cluster_id: str, admin=Depends(get_admin_user)):
    if cluster_id in _circuit_breakers:
        _circuit_breakers[cluster_id] = {"state": "closed", "failures": 0, "last_failure": 0}
        return {"status": "success", "message": f"Circuit breaker for {cluster_id} reset to closed."}
    return {"status": "error", "message": "Cluster ID not found in circuit breakers."}

@router.post("/test")
async def test_forwarding(cluster_id: str, request: Request, admin=Depends(get_admin_user), session: AsyncSession=Depends(get_db)):
    from app.models.commercial_cluster_registry import CommercialClusterRegistry
    from sqlalchemy import select
    res = await session.execute(select(CommercialClusterRegistry).where(CommercialClusterRegistry.cluster_id == cluster_id))
    cluster = res.scalar_one_or_none()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
        
    forwarder = CommercialCrossClusterForwarder(session)
    if not forwarder.should_forward_request(cluster):
        return {"status": "blocked", "reason": "should_forward_request returned False (check settings or cluster status)"}
        
    # Simulate a tiny non-stream request (this implies cluster must support some healthcheck or simple echo if real)
    # Actually just checking configuration and building headers
    headers = forwarder.build_forward_headers(request.headers, cluster, "test-correlation-id")
    
    return {
        "status": "dry_run_success",
        "target_url": cluster.forwarding_base_url,
        "generated_headers": headers
    }
