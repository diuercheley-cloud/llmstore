import json

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.backend_registry import ensure_default_backends
from app.utils.model_prompting import detect_architecture, detect_prompt_template


async def ensure_default_model(session: AsyncSession) -> ModelRegistry:
    settings = get_settings()
    backends = await ensure_default_backends(session)
    gemma_model = await _ensure_model_entry(
        session,
        model_id=settings.model_id,
        model_alias="gemma",
        model_file=settings.model_file,
        backend=backends["gemma-local"],
        is_default=True,
        is_active=True,
        metadata=_build_metadata(
            recommended_quantization="Q4_K_M",
            gpu_profile="RTX 4050 6GB",
            backend_name="gemma-local",
            architecture="gemma",
        ),
    )
    if "fallback-local" in backends:
        await _ensure_fallback_route(session, gemma_model, backends["fallback-local"])
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Seeding models. LMStudio enabled: {settings.lmstudio_enabled}, backends: {list(backends.keys())}")

    if settings.lmstudio_enabled and "lmstudio-local" in backends:
        logger.info(f"Seeding LMStudio model: {settings.lmstudio_default_model}")
        lmstudio_model = await _ensure_model_entry(
            session,
            model_id=settings.lmstudio_default_model,
            model_alias="lmstudio",
            model_file="",
            backend=backends["lmstudio-local"],
            is_default=True,
            is_active=True,
            provider="openai_compatible",
            metadata=_build_metadata(
                recommended_quantization="",
                gpu_profile="",
                backend_name="lmstudio-local",
                architecture="nemotron",
            ),
        )
        gemma_model.is_default = False
    existing_defaults = (
        await session.execute(select(ModelRegistry).where(ModelRegistry.id != gemma_model.id, ModelRegistry.is_default.is_(True)))
    ).scalars().all()
    for item in existing_defaults:
        item.is_default = False
    return gemma_model


def _build_metadata(
    *,
    recommended_quantization: str,
    gpu_profile: str,
    backend_name: str,
    architecture: str | None = None,
) -> str:
    payload = {
        "recommended_quantization": recommended_quantization,
        "gpu_profile": gpu_profile,
        "backend": "llama.cpp",
        "backend_name": backend_name,
    }
    if architecture:
        payload["architecture"] = architecture
    return json.dumps(payload)


async def _ensure_model_entry(
    session: AsyncSession,
    *,
    model_id: str,
    model_alias: str,
    model_file: str,
    backend: InferenceBackend,
    is_default: bool,
    is_active: bool,
    metadata: str,
    provider: str = "llama.cpp",
) -> ModelRegistry:
    settings = get_settings()
    result = await session.execute(
        select(ModelRegistry)
        .options(
            selectinload(ModelRegistry.inference_backend),
            selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
        )
        .where(or_(ModelRegistry.model_id == model_id, ModelRegistry.model_alias == model_alias))
    )
    model = result.scalar_one_or_none()
    detected_architecture = detect_architecture(
        model_id=model_id,
        model_file=model_file,
        model_alias=model_alias,
        metadata_json=metadata,
    )
    detected_prompt_template = detect_prompt_template(
        model_id=model_id,
        model_file=model_file,
        model_alias=model_alias,
        metadata_json=metadata,
    )
    if model is None:
        model = ModelRegistry(
            model_id=model_id,
            model_alias=model_alias,
            inference_backend_id=backend.id,
            provider=provider,
            model_file=model_file,
            context_length=settings.max_context_tokens,
            is_active=is_active,
            is_default=is_default,
            status="configured" if is_active else "optional-disabled",
            prompt_template=detected_prompt_template,
            metadata_json=metadata,
        )
        session.add(model)
        await session.flush()
    else:
        model.model_alias = model_alias
        model.inference_backend_id = backend.id
        model.provider = provider
        model.model_file = model_file
        model.context_length = settings.max_context_tokens
        model.is_default = is_default
        model.is_active = is_active
        model.status = "configured" if is_active else "optional-disabled"
        model.prompt_template = detected_prompt_template
        model.metadata_json = metadata
    if detected_architecture and model.metadata_json != metadata:
        model.metadata_json = metadata
    await _ensure_default_route(session, model, backend)
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
            state="disabled" if not backend.is_active else "healthy",
        )
        session.add(route)
        await session.flush()
        return
    route.priority = 2
    route.weight = 100
    if not backend.is_active:
        route.state = "disabled"
    elif route.state == "disabled":
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
            state="healthy" if backend.is_active else "disabled",
        )
        session.add(route)
        await session.flush()
        return
    route.priority = 1
    route.weight = 100
    if not backend.is_active:
        route.state = "disabled"
    elif route.state == "disabled":
        route.state = "healthy"
