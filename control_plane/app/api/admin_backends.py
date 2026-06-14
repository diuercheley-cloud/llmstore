# Owner: platform-ops
import asyncio
import json
import logging
import uuid

from app.api.deps import get_circuit_breaker, get_inference_proxy
from app.core.config import get_settings
from app.core.time import utc_now
from app.services.runtime_dependencies import get_db_session
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from app.models.core.security_event import SecurityEvent
from app.schemas.admin import InferenceBackendCreate, InferenceBackendPatch
from app.services.admin_model_management import (
    backend_container_snapshot,
    backend_runtime_capabilities,
    backend_service_name,
    run_backend_docker_command,
)
from app.services.auth import require_admin
from app.services.backend_registry import ensure_default_backends
from app.services.inference_proxy import InferenceProxy
from app.services.security_monitor import log_security_event
from app.services.backend_lifecycle.manager import BackendLifecycleManager
from app.services.backend_lifecycle.providers import (
    DockerProvider,
    KubernetesProvider,
    LocalProcessProvider,
    ProviderUnavailableError,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.model_policy import MODEL_REGISTRY_ROUTING_LOADS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-backends"], dependencies=[Depends(require_admin)])
settings = get_settings()


def _load_backend_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_test_backend(backend: InferenceBackend) -> bool:
    metadata = _load_backend_metadata(backend.metadata_json)
    return bool(metadata.get("test_backend")) or backend.name.startswith("fallback-")


def _serialize_backend_admin(backend: InferenceBackend, health: dict | None = None) -> dict:
    runtime = backend_container_snapshot(backend)
    return {
        "id": str(backend.id),
        "name": backend.name,
        "provider": backend.provider,
        "backend_url": backend.backend_url,
        "healthcheck_path": backend.healthcheck_path,
        "is_active": backend.is_active,
        "is_default": backend.is_default,
        "status": backend.status,
        "max_parallel_requests": backend.max_parallel_requests,
        "current_running": backend.current_running,
        "metadata_json": backend.metadata_json,
        "service_name": backend_service_name(backend),
        "docker": runtime,
        "health": health,
        "created_at": backend.created_at.isoformat(),
        "updated_at": backend.updated_at.isoformat(),
    }


def _select_lifecycle_provider(backend: InferenceBackend) -> str:
    metadata = _load_backend_metadata(backend.metadata_json)
    provider_hint = metadata.get("lifecycle_provider") or ""
    if provider_hint:
        return provider_hint
    service_name = backend_service_name(backend)
    if service_name:
        return "docker"
    if backend.provider == "llama.cpp":
        return "local_process"
    return "local_process"


def _build_lifecycle_manager(session: AsyncSession, backend: InferenceBackend | None = None) -> BackendLifecycleManager:
    provider_type = "local_process"
    if backend is not None:
        provider_type = _select_lifecycle_provider(backend)

    provider_map = {
        "local_process": LocalProcessProvider(),
        "docker": DockerProvider(),
        "kubernetes": KubernetesProvider(),
    }
    provider = provider_map.get(provider_type, LocalProcessProvider())
    return BackendLifecycleManager(
        db=session,
        provider=provider,
        audit_callback=lambda action, details: asyncio.create_task(
            _log_lifecycle_event(session, action, details)
        ),
    )


async def _log_lifecycle_event(session: AsyncSession, action: str, details: dict) -> None:
    try:
        await log_security_event(
            session,
            event_type=f"backend_lifecycle_{action}",
            severity="high",
            title=f"Backend lifecycle {action}",
            details=details,
        )
    except Exception as exc:
        logger.error("failed to log lifecycle event: %s", exc)


def get_lifecycle_manager(
    session: AsyncSession = Depends(get_db_session),
) -> BackendLifecycleManager:
    return _build_lifecycle_manager(session)


@router.get("/backends")
async def list_backends(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await ensure_default_backends(session)
    await session.commit()
    rows = (await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))).scalars().all()
    health_results = await asyncio.gather(*[proxy.health_backend(item) for item in rows])
    return [_serialize_backend_admin(item, health) for item, health in zip(rows, health_results)]


@router.post("/backends", status_code=201)
async def create_backend(payload: InferenceBackendCreate, session: AsyncSession = Depends(get_db_session)):
    existing = await session.execute(select(InferenceBackend).where(InferenceBackend.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="backend name already exists")
    if payload.is_default:
        defaults = (await session.execute(select(InferenceBackend).where(InferenceBackend.is_default.is_(True)))).scalars().all()
        for item in defaults:
            item.is_default = False
    backend = InferenceBackend(**payload.model_dump())
    session.add(backend)
    await session.commit()
    await session.refresh(backend)
    return {
        "id": str(backend.id),
        "name": backend.name,
        "provider": backend.provider,
        "backend_url": backend.backend_url,
        "healthcheck_path": backend.healthcheck_path,
        "is_active": backend.is_active,
        "is_default": backend.is_default,
        "status": backend.status,
        "max_parallel_requests": backend.max_parallel_requests,
        "current_running": backend.current_running,
        "metadata_json": backend.metadata_json,
    }


@router.post("/backends/test-connection")
async def test_backend_connection(
    payload: InferenceBackendCreate,
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    base_url = payload.backend_url
    api_key = None
    if payload.metadata_json:
        try:
            metadata = json.loads(payload.metadata_json)
            api_key = metadata.get("api_key")
        except json.JSONDecodeError:
            pass
    ok = await proxy.health_url(base_url, payload.healthcheck_path)
    if not ok and payload.provider == "openai_compatible":
         ok = await proxy.health_url(base_url, "/v1/models")
         if not ok:
             ok = await proxy.health_url(base_url, "/models")
    return {"ok": ok}


@router.post("/backends/list-models")
async def list_backend_models(
    payload: InferenceBackendCreate,
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    base_url = payload.backend_url
    api_key = None
    if payload.metadata_json:
        try:
            metadata = json.loads(payload.metadata_json)
            api_key = metadata.get("api_key")
        except json.JSONDecodeError:
            pass
    return await proxy.list_models(base_url=base_url, api_key=api_key)


@router.patch("/backends/{backend_id}")
async def patch_backend(
    backend_id: uuid.UUID,
    payload: InferenceBackendPatch,
    session: AsyncSession = Depends(get_db_session),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    patch_data = payload.model_dump(exclude_unset=True)
    if "name" in patch_data and patch_data["name"] != backend.name:
        existing = await session.execute(select(InferenceBackend).where(InferenceBackend.name == patch_data["name"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="backend name already exists")
    if patch_data.get("is_default") is True:
        defaults = (await session.execute(select(InferenceBackend).where(InferenceBackend.is_default.is_(True), InferenceBackend.id != backend_id))).scalars().all()
        for item in defaults:
            item.is_default = False
    for key, value in patch_data.items():
        setattr(backend, key, value)
    backend.updated_at = utc_now()
    await session.commit()
    await session.refresh(backend)
    return {
        "id": str(backend.id),
        "name": backend.name,
        "provider": backend.provider,
        "backend_url": backend.backend_url,
        "healthcheck_path": backend.healthcheck_path,
        "is_active": backend.is_active,
        "is_default": backend.is_default,
        "status": backend.status,
        "max_parallel_requests": backend.max_parallel_requests,
        "current_running": backend.current_running,
        "metadata_json": backend.metadata_json,
    }


@router.get("/backends/{backend_id}/health")
async def backend_health(
    backend_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    return {
        "backend": _serialize_backend_admin(backend, await proxy.health_backend(backend)),
        "docker": backend_container_snapshot(backend),
    }


@router.get("/backends/{backend_id}/logs")
async def backend_logs(
    backend_id: uuid.UUID,
    tail: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    service_name = backend_service_name(backend)
    if not service_name:
        raise HTTPException(status_code=409, detail="backend is not mapped to a compose service")
    result = run_backend_docker_command(backend, "logs", "--tail", str(tail), service_name, timeout_seconds=30)
    if not result.ok:
        raise HTTPException(status_code=409, detail=result.detail or result.stderr or "backend logs unavailable")
    return {
        "backend_id": str(backend.id),
        "backend_name": backend.name,
        "service_name": service_name,
        "tail": tail,
        "logs": result.stdout[-20000:],
    }


async def _run_backend_action(
    backend_id: uuid.UUID,
    action: str,
    session: AsyncSession,
) -> dict:
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")

    manager = _build_lifecycle_manager(session, backend)

    try:
        if action == "start":
            result = await manager.start_backend(backend_id)
        elif action == "stop":
            result = await manager.stop_backend(backend_id)
        elif action == "restart":
            result = await manager.restart_backend(backend_id)
        else:
            raise HTTPException(status_code=400, detail=f"unknown action: {action}")
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if not result.success:
        raise HTTPException(status_code=409, detail=result.message)

    backend = await session.get(InferenceBackend, backend_id)
    return {
        "status": action,
        "backend_id": str(backend.id),
        "backend_name": backend.name,
        "lifecycle_result": result.model_dump(),
        "docker": backend_container_snapshot(backend) if backend_service_name(backend) else None,
    }


@router.post("/backends/{backend_id}/start")
async def start_backend(backend_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    return await _run_backend_action(backend_id, "start", session)


@router.post("/backends/{backend_id}/stop")
async def stop_backend(backend_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    return await _run_backend_action(backend_id, "stop", session)


@router.post("/backends/{backend_id}/restart")
async def restart_backend(backend_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    return await _run_backend_action(backend_id, "restart", session)


@router.get("/backends/{backend_id}/lifecycle/observed")
async def backend_lifecycle_observed(
    backend_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    manager = _build_lifecycle_manager(session, backend)
    observed = await manager.get_observed_state(backend_id)
    return {
        "backend_id": str(backend_id),
        "observed_state": observed.model_dump(),
        "capabilities": manager.capabilities().model_dump(),
    }


@router.post("/backends/{backend_id}/lifecycle/reconcile")
async def backend_lifecycle_reconcile(
    backend_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    backend = await session.get(InferenceBackend, backend_id)
    if backend is None:
        raise HTTPException(status_code=404, detail="backend not found")
    manager = _build_lifecycle_manager(session, backend)
    result = await manager.reconcile_one(backend_id)
    return result


@router.post("/backends/lifecycle/reconcile-all")
async def backends_lifecycle_reconcile_all(
    session: AsyncSession = Depends(get_db_session),
):
    manager = _build_lifecycle_manager(session)
    results = await manager.reconcile_all()
    return {"reconciled": len(results), "results": results}


@router.get("/backends/lifecycle/drift-history")
async def backend_lifecycle_drift_history(
    session: AsyncSession = Depends(get_db_session),
    backend_id: uuid.UUID | None = Query(default=None),
):
    manager = _build_lifecycle_manager(session)
    drifts = manager.drift_history()
    if backend_id:
        drifts = [d for d in drifts if d.backend_id == backend_id]
    return {"drifts": [d.model_dump() for d in drifts]}


@router.post("/backends/circuit-breaker/reset")
async def reset_backend_circuit_breaker():
    breaker = get_circuit_breaker()
    await breaker.reset()
    return {
        "status": "ok",
        "detail": "circuit breaker reset",
        "reset_at": utc_now().isoformat(),
        "scope": "in-memory control-plane process",
    }


@router.get("/backends/health")
async def backends_health(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    rows = (await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))).scalars().all()
    return {
        "generated_at": utc_now().isoformat(),
        "backends": await asyncio.gather(*[proxy.health_backend(item) for item in rows]),
    }


@router.get("/backends/routing")
async def backends_routing(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    backend_rows = (
        await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))
    ).scalars().all()
    backend_health_list = await asyncio.gather(*[proxy.health_backend(row) for row in backend_rows])
    backend_health = {item["backend_id"]: item for item in backend_health_list}
    models = (
        await session.execute(
            select(ModelRegistry)
            .options(*MODEL_REGISTRY_ROUTING_LOADS)
            .order_by(ModelRegistry.created_at.asc())
        )
    ).scalars().all()
    model_rows = []
    summary = {"healthy": 0, "degraded": 0, "unhealthy": 0, "disabled": 0}
    for item in models:
        routes = []
        for route in sorted(
            item.backend_routes,
            key=lambda entry: (entry.priority, -(entry.weight or 0), entry.created_at),
        ):
            backend = route.inference_backend
            if backend is None:
                continue
            summary[route.state] = summary.get(route.state, 0) + 1
            backend_snapshot = backend_health.get(str(backend.id), {})
            routes.append(
                {
                    "route_id": str(route.id) if route.id else None,
                    "backend_id": str(backend.id),
                    "backend_name": backend.name,
                    "backend_url": backend.backend_url,
                    "provider": backend.provider,
                    "priority": route.priority,
                    "weight": route.weight,
                    "state": route.state,
                    "health": backend_snapshot.get("ok"),
                    "latency_ms": backend_snapshot.get("latency_ms"),
                    "backend_is_active": backend.is_active,
                    "backend_status": backend.status,
                    "is_test_backend": _is_test_backend(backend),
                    "eligible_for_routing": bool(backend.is_active and route.state != "disabled"),
                }
            )
        model_rows.append(
            {
                "id": str(item.id),
                "model_id": item.model_id,
                "model_alias": item.model_alias,
                "is_default": item.is_default,
                "routing_policy": "weighted_priority_fallback",
                "routes": routes,
            }
        )
    return {
        "generated_at": utc_now().isoformat(),
        "summary": summary,
        "models": model_rows,
    }
