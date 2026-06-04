import json

from app.core.config import get_settings
from app.models.inference_backend import InferenceBackend
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_default_backends(session: AsyncSession) -> dict[str, InferenceBackend]:
    settings = get_settings()
    existing = {
        item.name: item
        for item in (await session.execute(select(InferenceBackend))).scalars().all()
    }
    backends = [
        {
            "name": "gemma-local",
            "provider": "llama.cpp",
            "backend_url": settings.data_plane_base_url,
            "healthcheck_path": "/health",
            "is_active": True,
            "is_default": True,
            "status": "configured",
            "max_parallel_requests": 1,
            "metadata_json": json.dumps({"service_name": "data-plane-gemma"}),
        },
        {
            "name": "ollama-local",
            "provider": "ollama",
            "backend_url": settings.ollama_base_url,
            "healthcheck_path": "/api/tags",
            "is_active": False,
            "is_default": False,
            "status": "optional",
            "max_parallel_requests": 1,
            "metadata_json": json.dumps({"service_name": "data-plane-ollama"}),
        },
        {
            "name": "lmstudio-local",
            "provider": "openai_compatible",
            "backend_url": settings.lmstudio_base_url,
            "healthcheck_path": "/models",
            "is_active": settings.lmstudio_enabled,
            "is_default": settings.lmstudio_enabled,
            "status": "configured" if settings.lmstudio_enabled else "optional-disabled",
            "max_parallel_requests": 8,
            "metadata_json": json.dumps({"service_name": "data-plane-lmstudio", "api_key": settings.lmstudio_api_key}),
        },
        {
            "name": "vllm-local",
            "provider": "vllm",
            "backend_url": settings.vllm_base_url,
            "healthcheck_path": "/health",
            "is_active": settings.vllm_backend_enabled,
            "is_default": False,
            "status": "configured" if settings.vllm_backend_enabled else "optional-disabled",
            "max_parallel_requests": settings.vllm_max_concurrent_requests,
            "metadata_json": json.dumps({"service_name": "data-plane-vllm", "api_key": settings.vllm_api_key}),
        },
        {
            "name": "fallback-local",
            "provider": "llama.cpp",
            "backend_url": "http://data-plane-mock:8081",
            "healthcheck_path": "/health",
            "is_active": False,
            "is_default": False,
            "status": "test-disabled",
            "max_parallel_requests": 8,
            "metadata_json": json.dumps({"service_name": "data-plane-mock", "test_backend": True}),
        },
    ]
    created_or_updated: dict[str, InferenceBackend] = {}
    for payload in backends:
        backend = existing.get(payload["name"])
        if backend is None:
            backend = InferenceBackend(**payload)
            session.add(backend)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                # Re-fetch all existing backends after rollback
                existing = {
                    item.name: item
                    for item in (await session.execute(select(InferenceBackend))).scalars().all()
                }
                backend = existing.get(payload["name"])
                if backend is None:
                    continue
        else:
            for key, value in payload.items():
                if backend.name == "ollama-local" and key in {"is_active", "status"}:
                    continue
                setattr(backend, key, value)
        created_or_updated[backend.name] = backend

    default_backend = created_or_updated.get("gemma-local")
    if default_backend:
        for item in created_or_updated.values():
            item.is_default = item.id == default_backend.id
    return created_or_updated

