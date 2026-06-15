from app.api.deps import get_db_session
from app.models.core.inference_backend import InferenceBackend
from app.services.inference.router import InferenceRouter
from app.services.inference_backends import (
    Capability,
    OpenAICompatibleBackend,
    TGIBackend,
    VLLMBackend,
)
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/inference", tags=["admin-inference"])


@router.get("/backends")
async def list_inference_backends(session: AsyncSession = Depends(get_db_session)):
    stmt = select(InferenceBackend)
    result = await session.execute(stmt)
    backends = result.scalars().all()

    output = []
    for b in backends:
        # Create adapter to check health
        adapter = None
        if b.provider == "vllm":
            adapter = VLLMBackend(b.name, b.backend_url)
        elif b.provider == "tgi":
            adapter = TGIBackend(b.name, b.backend_url)
        elif b.provider == "openai_compatible":
            adapter = OpenAICompatibleBackend(b.name, b.backend_url)

        health_status = False
        if adapter:
            health_status = await adapter.health()

        output.append(
            {
                "id": str(b.id),
                "name": b.name,
                "provider": b.provider,
                "backend_url": b.backend_url,
                "is_active": b.is_active,
                "health": "healthy" if health_status else "unhealthy",
                "capabilities": [c.value for c in Capability if adapter.supports_capability(c)]
                if adapter
                else [],
            }
        )
    return output


from app.models.core.inference_routing_decision import InferenceRoutingDecision


@router.get("/routing/last-decision")
async def get_last_routing_decision(session: AsyncSession = Depends(get_db_session)):
    stmt = (
        select(InferenceRoutingDecision)
        .order_by(InferenceRoutingDecision.created_at.desc())
        .limit(100)
    )
    result = await session.execute(stmt)
    decisions = result.scalars().all()

    output = []
    for d in decisions:
        output.append(
            {
                "id": str(d.id),
                "request_id": d.request_id,
                "tenant_id": d.tenant_id,
                "client_id": d.client_id,
                "selected_backend": d.selected_backend,
                "selected_model": d.selected_model,
                "candidate_backends": d.candidate_backends,
                "routing_policy_version": d.routing_policy_version,
                "reason": d.reason,
                "latency_ms": d.latency_ms,
                "success": d.success,
                "error_code": d.error_code,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
        )

    return {"log": output, "last_decision": output[0] if output else None}


@router.post("/routing/simulate")
async def simulate_routing(
    model: str,
    capability: Capability,
    tenant_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    inference_router = InferenceRouter(session)
    adapter, reason = await inference_router.get_best_backend(
        model,
        capability,
        tenant_id,
        request_id="simulation-req",
        client_id="admin-client",
        success=True,
    )
    await session.commit()

    return {
        "selected_backend": adapter.name if adapter else None,
        "reason": reason,
        "decision_log": inference_router.get_last_decision(),
    }


@router.delete("/routing/decisions/cleanup")
async def cleanup_routing_decisions(
    retention_days: int | None = None, session: AsyncSession = Depends(get_db_session)
):
    inference_router = InferenceRouter(session)
    deleted_count = await inference_router.cleanup_old_decisions(retention_days)
    await session.commit()
    return {"deleted_count": deleted_count}
