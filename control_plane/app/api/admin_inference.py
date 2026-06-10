from typing import Any, Dict, List, Optional

from app.api.deps import get_db_session
from app.services.inference.backends.base import Capability
from app.services.inference.router import InferenceRouter
from app.services.inference.backends.vllm_backend import VLLMBackend
from app.services.inference.backends.tgi_backend import TGIBackend
from app.services.inference.backends.openai_compatible_backend import OpenAICompatibleBackend
from app.models.core.inference_backend import InferenceBackend
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
            
        output.append({
            "id": str(b.id),
            "name": b.name,
            "provider": b.provider,
            "backend_url": b.backend_url,
            "is_active": b.is_active,
            "health": "healthy" if health_status else "unhealthy",
            "capabilities": [c.value for c in Capability if adapter.supports_capability(c)] if adapter else []
        })
    return output


@router.get("/routing/last-decision")
async def get_last_routing_decision(session: AsyncSession = Depends(get_db_session)):
    inference_router = InferenceRouter(session)
    # This won't work across requests without persistence, but for demo purposes:
    return {"message": "In-memory routing log only available in current session", "log": inference_router.routing_log}


@router.post("/routing/simulate")
async def simulate_routing(
    model: str, 
    capability: Capability, 
    tenant_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    inference_router = InferenceRouter(session)
    adapter, reason = await inference_router.get_best_backend(model, capability, tenant_id)
    
    return {
        "selected_backend": adapter.name if adapter else None,
        "reason": reason,
        "decision_log": inference_router.get_last_decision()
    }
