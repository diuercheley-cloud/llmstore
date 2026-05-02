import json

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.backend_registry import ensure_default_backends


async def ensure_default_model(session: AsyncSession) -> ModelRegistry:
    settings = get_settings()
    backends = await ensure_default_backends(session)
    default_backend = backends["gemma-local"]
    result = await session.execute(
        select(ModelRegistry)
        .options(selectinload(ModelRegistry.inference_backend))
        .where(ModelRegistry.model_id == settings.model_id)
    )
    model = result.scalar_one_or_none()
    metadata = json.dumps(
        {
            "recommended_quantization": "Q4_K_M",
            "gpu_profile": "RTX 4050 6GB",
            "backend": "llama.cpp",
        }
    )
    if model:
        model.model_alias = model.model_alias or "gemma"
        model.inference_backend_id = default_backend.id
        model.model_file = settings.model_file
        model.context_length = settings.max_context_tokens
        model.provider = "llama.cpp"
        model.is_default = True
        model.is_active = True
        model.status = "configured"
        model.metadata_json = metadata
        existing_defaults = (
            await session.execute(select(ModelRegistry).where(ModelRegistry.id != model.id, ModelRegistry.is_default.is_(True)))
        ).scalars().all()
        for item in existing_defaults:
            item.is_default = False
        await _ensure_default_route(session, model, default_backend)
        if "fallback-local" in backends:
            await _ensure_fallback_route(session, model, backends["fallback-local"])
        return model
    model = ModelRegistry(
        model_id=settings.model_id,
        model_alias="gemma",
        inference_backend_id=default_backend.id,
        provider="llama.cpp",
        model_file=settings.model_file,
        context_length=settings.max_context_tokens,
        is_default=True,
        status="configured",
        metadata_json=metadata,
    )
    session.add(model)
    await session.flush()
    await _ensure_default_route(session, model, default_backend)
    if "fallback-local" in backends:
        await _ensure_fallback_route(session, model, backends["fallback-local"])
    return model


async def _ensure_fallback_route(session: AsyncSession, model: ModelRegistry, backend: InferenceBackend) -> None:
    result = await session.execute(
        select(ModelBackendRoute).where(
            ModelBackendRoute.model_registry_id == model.id,
            ModelBackendRoute.inference_backend_id == backend.id,
        )
    )
    route = result.scalar_one_or_none()
    if route is None:
        route = ModelBackendRoute(
            model_registry_id=model.id,
            inference_backend_id=backend.id,
            priority=2,
            weight=100,
            state="healthy",
        )
        session.add(route)
        await session.flush()
        return
    route.priority = 2
    route.weight = 100
    if route.state == "disabled":
        route.state = "healthy"


async def _ensure_default_route(session: AsyncSession, model: ModelRegistry, backend: InferenceBackend) -> None:
    result = await session.execute(
        select(ModelBackendRoute).where(
            ModelBackendRoute.model_registry_id == model.id,
            ModelBackendRoute.inference_backend_id == backend.id,
        )
    )
    route = result.scalar_one_or_none()
    if route is None:
        route = ModelBackendRoute(
            model_registry_id=model.id,
            inference_backend_id=backend.id,
            priority=1,
            weight=100,
            state="healthy",
        )
        session.add(route)
        await session.flush()
        return
    route.priority = 1
    route.weight = 100
    if route.state == "disabled":
        route.state = "healthy"
