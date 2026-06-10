import asyncio
import json
import time
import uuid

from app.api.deps import get_db_session, get_inference_proxy
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.billing.billing_plan import BillingPlan
from app.models.core.client import Client
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from app.models.core.request_log import RequestLog
from app.schemas.admin import (
    BackendRouteInput,
    BackendRoutePatch,
    ModelDeleteRequest,
    ModelPromptTestRequest,
    ModelRegistryCreate,
    ModelRegistryPatch,
    ModelReloadResponse,
    RoutingExplainRequest,
    RoutingExplainResponse,
)
from app.services.admin_model_management import (
    architecture_for_model,
    archive_model_identity,
    backend_container_snapshot,
    backend_service_name,
    detect_quantization,
    display_name_for_model,
    ensure_model_file_exists,
    list_model_files,
    merge_metadata,
    parse_metadata,
    prompt_template_for_payload,
    reasoning_defaults_for_model,
    remove_model_routes,
    resolve_models_dir,
    sanitize_model_filename,
    sync_allowed_plans,
)
from app.services.auth import require_admin
from app.services.backend_registry import ensure_default_backends
from app.services.inference_proxy import InferenceProxy
from app.services.model_policy import (
    MODEL_REGISTRY_ROUTING_LOADS,
    apply_routing_policy,
    ensure_model_routing_loaded,
    get_model_by_id,
    get_routing_candidates,
    plan_routing_order,
    resolve_requested_model,
    serialize_routing_table,
)
from app.services.model_registry import ensure_default_model
from app.services.models.model_provenance import summarize_model_provenance
from app.services.models.signed_model_registry import latest_registry_map
from app.services.security_monitor import log_security_event
from app.utils.tool_calling import model_supports_native_tools
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

settings = get_settings()

router = APIRouter(prefix="/admin", tags=["admin-models"], dependencies=[Depends(require_admin)])


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


def _serialize_model_admin(model: ModelRegistry, health_map: dict[str, dict] | None = None) -> dict:
    ensure_model_routing_loaded(model)
    metadata = parse_metadata(model.metadata_json)
    architecture = architecture_for_model(model)
    reasoning = reasoning_defaults_for_model(model)
    backend_health = health_map.get(str(model.inference_backend_id)) if health_map and model.inference_backend_id else None
    is_chat = model.provider in {"llama.cpp", "ollama", "vllm", "openai_compatible", "openrouter", "openai", "anthropic", "deepseek"}
    capabilities = {
        "supports_chat": is_chat,
        "supports_streaming": is_chat,
        "supports_embeddings": "embedding" in model.model_id.lower() or metadata.get("type") == "embedding",
        "supports_responses": is_chat,
        "supports_tools": is_chat and model_supports_native_tools(model.provider, model.metadata_json),
    }

    return {
        "id": str(model.id),
        "display_name": display_name_for_model(model),
        "model_id": model.model_id,
        "model_alias": model.model_alias,
        "inference_backend_id": str(model.inference_backend_id) if model.inference_backend_id else None,
        "backend_name": model.inference_backend.name if model.inference_backend else None,
        "backend_url": model.inference_backend.backend_url if model.inference_backend else None,
        "provider": model.provider,
        "model_file": model.model_file,
        "status": model.status,
        "is_active": model.is_active,
        "is_default": model.is_default,
        "context_length": model.context_length,
        "prompt_template": model.prompt_template,
        "architecture": architecture,
        "quantization": detect_quantization(model.model_file),
        "allow_reasoning": reasoning["allow_reasoning"],
        "include_reasoning_default": reasoning["include_reasoning_default"],
        "metadata_json": model.metadata_json,
        "metadata": metadata,
        "capabilities": capabilities,
        "routes": serialize_routing_table(model),
        "backend_health": backend_health,
        "created_at": model.created_at.isoformat(),
        "updated_at": model.updated_at.isoformat(),
    }


async def _sync_model_backend_routes(session: AsyncSession, model: ModelRegistry, routes_payload: list[dict]) -> None:
    existing = {
        item.inference_backend_id: item
        for item in (
            await session.execute(
                select(ModelBackendRoute).where(ModelBackendRoute.model_registry_id == model.id)
            )
        ).scalars().all()
    }
    keep_backend_ids = set()
    for route_data in routes_payload:
        backend_id = route_data["inference_backend_id"]
        if await session.get(InferenceBackend, backend_id) is None:
            raise HTTPException(status_code=404, detail="backend not found")
        keep_backend_ids.add(backend_id)
        route = existing.get(backend_id)
        if route is None:
            route = ModelBackendRoute(model_registry_id=model.id, **route_data)
            session.add(route)
            continue
        route.priority = route_data["priority"]
        route.weight = route_data["weight"]
        route.state = route_data["state"]
        route.updated_at = utc_now()
    for backend_id, route in existing.items():
        if backend_id not in keep_backend_ids:
            await session.delete(route)


@router.get("/models")
async def get_models(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await ensure_default_backends(session)
    await session.flush()
    result = await session.execute(
        select(ModelRegistry)
        .options(*MODEL_REGISTRY_ROUTING_LOADS)
        .order_by(ModelRegistry.created_at.desc())
    )
    registry = result.scalars().all()
    backends = (
        await session.execute(select(InferenceBackend).order_by(InferenceBackend.created_at.asc()))
    ).scalars().all()
    backend_health = await asyncio.gather(*[proxy.health_backend(item) for item in backends])
    health_map = {item["backend_id"]: item for item in backend_health}
    supply_chain_map = await latest_registry_map(session)
    plans = (await session.execute(select(BillingPlan).order_by(BillingPlan.created_at.asc()))).scalars().all()
    registry_payload = []
    for item in registry:
        payload = _serialize_model_admin(item, health_map)
        trust_entry = supply_chain_map.get(item.model_alias or item.model_id) or supply_chain_map.get(item.model_id)
        if trust_entry is not None:
            payload["supply_chain"] = {
                "registry_entry_id": str(trust_entry.id),
                "trust_state": trust_entry.trust_state,
                "checksum_sha256": trust_entry.checksum_sha256,
                "manifest_hash": trust_entry.manifest_hash,
                "approved_at": trust_entry.approved_at.isoformat() if trust_entry.approved_at else None,
                "approved_by": trust_entry.approved_by,
                "provenance_summary": await summarize_model_provenance(session, trust_entry.provenance_id),
            }
        else:
            payload["supply_chain"] = {
                "registry_entry_id": None,
                "trust_state": "untrusted",
                "checksum_sha256": None,
                "manifest_hash": None,
                "approved_at": None,
                "approved_by": None,
                "provenance_summary": None,
            }
        registry_payload.append(payload)
    return {
        "registry": [item for item in registry_payload if item["status"] != "soft-deleted"],
        "plan_access": [
            {
                "billing_plan_id": str(plan.id),
                "billing_plan_code": plan.code,
                "allowed_models_json": plan.allowed_models_json,
            }
            for plan in plans
        ],
        "backends": [_serialize_backend_admin(item, health_map.get(str(item.id))) for item in backends],
    }


@router.get("/models/files")
async def get_model_files(session: AsyncSession = Depends(get_db_session)):
    models_dir = resolve_models_dir()
    files = await list_model_files(session)
    warning = None
    if not models_dir.exists():
        warning = f"models directory not found: {models_dir}"
    elif not models_dir.is_dir():
        warning = f"models path is not a directory: {models_dir}"
    elif not files:
        warning = f"Nenhum arquivo .gguf encontrado em {models_dir}"
    return {
        "models_dir": str(models_dir),
        "models_dir_exists": models_dir.exists(),
        "models_dir_is_dir": models_dir.is_dir(),
        "files": files,
        "warning": warning,
    }


@router.post("/models", status_code=201)
async def create_model(payload: ModelRegistryCreate, session: AsyncSession = Depends(get_db_session)):
    backend_id = payload.inference_backend_id
    if backend_id is not None and payload.create_backend is not None:
        raise HTTPException(status_code=409, detail="choose an existing backend or create a new one")
    if payload.create_backend is not None:
        existing_backend = await session.execute(
            select(InferenceBackend).where(InferenceBackend.name == payload.create_backend.name)
        )
        if existing_backend.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="backend name already exists")
        backend_payload = payload.create_backend.model_dump()
        backend = InferenceBackend(**backend_payload)
        session.add(backend)
        await session.flush()
        backend_id = backend.id
    if backend_id is not None and await session.get(InferenceBackend, backend_id) is None:
        raise HTTPException(status_code=404, detail="backend not found")
    try:
        model_file = sanitize_model_filename(payload.model_file, provider=payload.provider)
        if payload.provider == "llama.cpp":
            ensure_model_file_exists(model_file, provider=payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clauses = [ModelRegistry.model_id == payload.model_id]
    if payload.model_alias:
        clauses.append(ModelRegistry.model_alias == payload.model_alias)
    existing = await session.execute(select(ModelRegistry).where(or_(*clauses)))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="model id or alias already exists")
    metadata_json = merge_metadata(
        payload.metadata_json,
        {
            "display_name": payload.display_name,
            "allow_reasoning": payload.allow_reasoning,
            "include_reasoning_default": payload.include_reasoning_default,
        },
    )
    prompt_template = prompt_template_for_payload(
        prompt_template=payload.prompt_template,
        model_id=payload.model_id,
        model_file=model_file,
        model_alias=payload.model_alias,
        metadata_json=metadata_json,
    )
    if payload.is_default:
        defaults = (await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True)))).scalars().all()
        for item in defaults:
            item.is_default = False
    model = ModelRegistry(
        model_id=payload.model_id,
        model_alias=payload.model_alias,
        inference_backend_id=backend_id,
        provider=payload.provider,
        model_file=model_file,
        context_length=payload.context_length,
        is_active=payload.is_active,
        is_default=payload.is_default,
        status=payload.status,
        prompt_template=prompt_template,
        metadata_json=metadata_json,
    )
    session.add(model)
    await session.flush()
    routes_payload = [item.model_dump() for item in payload.backend_routes]
    if not routes_payload and backend_id is not None:
        routes_payload = [{"inference_backend_id": backend_id, "priority": 1, "weight": 100, "state": "healthy"}]
    if routes_payload:
        await _sync_model_backend_routes(session, model, routes_payload)
    try:
        await sync_allowed_plans(session, model=model, allowed_plan_codes=payload.allowed_plan_codes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await log_security_event(
        session,
        event_type="admin_model_created",
        severity="medium",
        title="Model created via Admin Lab",
        details={"model_id": model.model_id, "model_alias": model.model_alias, "provider": model.provider},
    )
    await session.commit()
    loaded_model = await get_model_by_id(session, model.id)
    if loaded_model is None:
        raise HTTPException(status_code=404, detail="model not found after create")
    return _serialize_model_admin(loaded_model)


@router.patch("/models/{model_id}")
async def patch_model(
    model_id: uuid.UUID,
    payload: ModelRegistryPatch,
    session: AsyncSession = Depends(get_db_session),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(*MODEL_REGISTRY_ROUTING_LOADS)
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    patch_data = payload.model_dump(exclude_unset=True)
    routes_payload = patch_data.pop("backend_routes", None)
    allowed_plan_codes = patch_data.pop("allowed_plan_codes", None)
    display_name = patch_data.pop("display_name", None) if "display_name" in patch_data else None
    allow_reasoning = patch_data.pop("allow_reasoning", None) if "allow_reasoning" in patch_data else None
    include_reasoning_default = patch_data.pop("include_reasoning_default", None) if "include_reasoning_default" in patch_data else None
    if "inference_backend_id" in patch_data and patch_data["inference_backend_id"] is not None:
        if await session.get(InferenceBackend, patch_data["inference_backend_id"]) is None:
            raise HTTPException(status_code=404, detail="backend not found")
    if "model_alias" in patch_data and patch_data["model_alias"] is not None:
        existing = await session.execute(
            select(ModelRegistry).where(ModelRegistry.model_alias == patch_data["model_alias"], ModelRegistry.id != model_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="model alias already exists")
    if patch_data.get("is_default") is True:
        defaults = (
            await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True), ModelRegistry.id != model_id))
        ).scalars().all()
        for item in defaults:
            item.is_default = False
    if patch_data.get("is_active") is False and model.is_default:
        raise HTTPException(status_code=409, detail="default model cannot be disabled")
    provider = patch_data.get("provider", model.provider)
    if "model_file" in patch_data:
        try:
            patch_data["model_file"] = sanitize_model_filename(patch_data["model_file"], provider=provider)
            if provider == "llama.cpp":
                ensure_model_file_exists(patch_data["model_file"], provider=provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    for key, value in patch_data.items():
        setattr(model, key, value)
    metadata_updates = {}
    if "display_name" in payload.model_fields_set:
        metadata_updates["display_name"] = display_name
    if "allow_reasoning" in payload.model_fields_set:
        metadata_updates["allow_reasoning"] = allow_reasoning
    if "include_reasoning_default" in payload.model_fields_set:
        metadata_updates["include_reasoning_default"] = include_reasoning_default
    if metadata_updates:
        model.metadata_json = merge_metadata(model.metadata_json, metadata_updates)
    if "prompt_template" in patch_data or "model_file" in patch_data or "provider" in patch_data or "model_alias" in patch_data:
        model.prompt_template = prompt_template_for_payload(
            prompt_template=model.prompt_template,
            model_id=model.model_id,
            model_file=model.model_file,
            model_alias=model.model_alias,
            metadata_json=model.metadata_json,
        )
    if routes_payload is not None:
        await _sync_model_backend_routes(session, model, routes_payload)
    elif patch_data.get("inference_backend_id") is not None:
        existing_route = next(
            (item for item in model.backend_routes if item.inference_backend_id == patch_data["inference_backend_id"]),
            None,
        )
        if existing_route is None:
            await _sync_model_backend_routes(
                session,
                model,
                [
                    *[{"inference_backend_id": route.inference_backend_id, "priority": route.priority, "weight": route.weight, "state": route.state} for route in model.backend_routes],
                    {"inference_backend_id": patch_data["inference_backend_id"], "priority": 1, "weight": 100, "state": "healthy"},
                ],
            )
    try:
        await sync_allowed_plans(session, model=model, allowed_plan_codes=allowed_plan_codes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    model.updated_at = utc_now()
    await log_security_event(
        session,
        event_type="admin_model_updated",
        severity="medium",
        title="Model updated via Admin Lab",
        details={"model_id": model.model_id, "model_alias": model.model_alias},
    )
    await session.commit()
    loaded_model = await get_model_by_id(session, model.id)
    if loaded_model is None:
        raise HTTPException(status_code=404, detail="model not found after update")
    return _serialize_model_admin(loaded_model)


@router.post("/models/{model_id}/set-default")
async def set_default_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    defaults = (
        await session.execute(select(ModelRegistry).where(ModelRegistry.is_default.is_(True), ModelRegistry.id != model_id))
    ).scalars().all()
    for item in defaults:
        item.is_default = False
    model.is_default = True
    model.is_active = True
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "default-updated", "id": str(model.id)}


@router.post("/models/{model_id}/routes")
async def create_model_route(
    model_id: uuid.UUID,
    payload: BackendRouteInput,
    session: AsyncSession = Depends(get_db_session),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(*MODEL_REGISTRY_ROUTING_LOADS)
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    if await session.get(InferenceBackend, payload.inference_backend_id) is None:
        raise HTTPException(status_code=404, detail="backend not found")
    if any(route.inference_backend_id == payload.inference_backend_id for route in model.backend_routes):
        raise HTTPException(status_code=409, detail="route already exists for this backend")
    routes_payload = [
        {"inference_backend_id": route.inference_backend_id, "priority": route.priority, "weight": route.weight, "state": route.state}
        for route in model.backend_routes
    ]
    routes_payload.append(payload.model_dump())
    await _sync_model_backend_routes(session, model, routes_payload)
    if model.inference_backend_id is None:
        model.inference_backend_id = payload.inference_backend_id
    model.updated_at = utc_now()
    await session.commit()
    loaded_model = await get_model_by_id(session, model.id)
    if loaded_model is None:
        raise HTTPException(status_code=404, detail="model not found after route create")
    return _serialize_model_admin(loaded_model)


@router.delete("/models/{model_id}/routes/{backend_id}")
async def delete_model_route(
    model_id: uuid.UUID,
    backend_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
):
    route = (
        await session.execute(
            select(ModelBackendRoute).where(
                ModelBackendRoute.model_registry_id == model_id,
                ModelBackendRoute.inference_backend_id == backend_id,
            )
        )
    ).scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="model backend route not found")
    await session.delete(route)
    model = await session.get(ModelRegistry, model_id)
    if model is not None and model.inference_backend_id == backend_id:
        model.inference_backend_id = None
        model.updated_at = utc_now()
    await session.commit()
    return {"status": "route-removed", "model_id": str(model_id), "backend_id": str(backend_id)}


@router.patch("/models/{model_id}/routes/{backend_id}")
async def patch_model_backend_route(
    model_id: uuid.UUID,
    backend_id: uuid.UUID,
    payload: BackendRoutePatch,
    session: AsyncSession = Depends(get_db_session),
):
    route = (
        await session.execute(
            select(ModelBackendRoute).where(
                ModelBackendRoute.model_registry_id == model_id,
                ModelBackendRoute.inference_backend_id == backend_id,
            )
        )
    ).scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="model backend route not found")
    patch_data = payload.model_dump(exclude_unset=True)
    for key, value in patch_data.items():
        setattr(route, key, value)
    route.updated_at = utc_now()
    await session.commit()
    await session.refresh(route)
    return {
        "id": str(route.id),
        "model_id": str(route.model_registry_id),
        "backend_id": str(route.inference_backend_id),
        "priority": route.priority,
        "weight": route.weight,
        "state": route.state,
        "updated_at": route.updated_at.isoformat(),
    }


@router.post("/models/{model_id}/enable")
async def enable_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = (
        await session.execute(
            select(ModelRegistry).options(selectinload(ModelRegistry.inference_backend)).where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    model.is_active = True
    model.status = "configured"
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "enabled", "id": str(model.id)}


@router.post("/models/{model_id}/disable")
async def disable_model(model_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)):
    model = await session.get(ModelRegistry, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    if model.is_default:
        raise HTTPException(status_code=409, detail="default model cannot be disabled")
    model.is_active = False
    model.status = "disabled"
    model.updated_at = utc_now()
    await session.commit()
    await session.refresh(model)
    return {"status": "disabled", "id": str(model.id)}


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: uuid.UUID,
    payload: ModelDeleteRequest,
    session: AsyncSession = Depends(get_db_session),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(selectinload(ModelRegistry.backend_routes))
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    if model.is_default:
        raise HTTPException(status_code=409, detail="default model cannot be removed")
    route_count = len(model.backend_routes)
    if route_count and not payload.confirm_route_removal:
        raise HTTPException(status_code=409, detail="model still has active backend routes; confirm route removal")
    request_count = (
        await session.execute(
            select(func.count(RequestLog.id)).where(
                or_(
                    RequestLog.model == model.model_id,
                    RequestLog.model == (model.model_alias or ""),
                )
            )
        )
    ).scalar_one()
    if payload.mode in {"hard", "register-only"} and request_count:
        raise HTTPException(status_code=409, detail="model has request history; use soft delete or disable it")
    removed_routes = await remove_model_routes(session, model)
    result_status = "deleted"
    if payload.mode == "soft" or (payload.mode == "auto" and request_count):
        archive_model_identity(model)
        result_status = "soft-deleted"
    else:
        await session.delete(model)
    await log_security_event(
        session,
        event_type="admin_model_deleted",
        severity="high",
        title="Model removed via Admin Lab",
        details={
            "model_id": model.model_id,
            "model_alias": model.model_alias,
            "mode": payload.mode,
            "request_count": int(request_count or 0),
            "removed_routes": removed_routes,
            "result": result_status,
        },
    )
    await session.commit()
    return {
        "status": result_status,
        "id": str(model_id),
        "request_count": int(request_count or 0),
        "removed_routes": removed_routes,
    }


@router.post("/models/{model_id}/test-prompt")
async def test_model_prompt(
    model_id: uuid.UUID,
    payload: ModelPromptTestRequest,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    model = (
        await session.execute(
            select(ModelRegistry)
            .options(
                selectinload(ModelRegistry.inference_backend),
                selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
            )
            .where(ModelRegistry.id == model_id)
        )
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="model not found")
    include_reasoning = payload.include_reasoning
    if include_reasoning is None:
        include_reasoning = bool(reasoning_defaults_for_model(model)["include_reasoning_default"])
    body = {
        "model": model.model_id,
        "messages": [{"role": "user", "content": payload.prompt}],
        "max_tokens": payload.max_tokens,
        "temperature": payload.temperature,
    }
    routes = plan_routing_order(model)
    backend_errors: list[dict] = []
    started = time.perf_counter()
    for attempt, route in enumerate(routes, start=1):
        backend = route.inference_backend
        if backend is None:
            continue
        try:
            result = await proxy.chat(
                body,
                False,
                include_reasoning,
                backend=backend.provider,
                backend_url=backend.backend_url,
                backend_name=backend.name,
                backend_id=backend.id,
                prompt_template=model.prompt_template,
                is_admin=True,
            )
            response_payload = json.loads(result.response.body.decode("utf-8"))
            usage = response_payload.get("usage") or {}
            content = ""
            if response_payload.get("choices"):
                message = response_payload["choices"][0].get("message") or {}
                content = message.get("content") or ""
            return {
                "response": content,
                "raw_response": response_payload,
                "model_used": model.model_id,
                "backend_used": backend.name,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "tokens": usage,
                "attempts": attempt,
                "fallback_used": attempt > 1,
                "include_reasoning": include_reasoning,
                "prompt_template": model.prompt_template,
                "backend_errors": backend_errors,
            }
        except HTTPException as exc:
            backend_errors.append(
                {
                    "backend_name": backend.name if backend else None,
                    "backend_id": str(route.inference_backend_id),
                    "status_code": exc.status_code,
                    "error": exc.detail,
                }
            )
    raise HTTPException(
        status_code=503,
        detail={
            "message": "all backend routes failed",
            "backend_errors": backend_errors,
        },
    )


@router.post("/routing/explain", response_model=RoutingExplainResponse)
async def explain_routing(
    payload: RoutingExplainRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Explains the routing decision for a given model and client.
    """
    client = await session.get(Client, payload.client_id, options=[selectinload(Client.billing_plan)])
    if not client:
        raise HTTPException(status_code=404, detail="client not found")

    selected_model, requested_model = await resolve_requested_model(
        session,
        client=client,
        requested_model=payload.model or "default",
    )

    all_candidates = get_routing_candidates(selected_model)

    routing_policy = None
    if client.billing_plan and client.billing_plan.routing_policy_json:
        try:
            routing_policy = json.loads(client.billing_plan.routing_policy_json)
        except json.JSONDecodeError:
            pass

    final_candidates = apply_routing_policy(selected_model, client, list(all_candidates))

    final_ids = {c.id for c in final_candidates}
    rejected = [c for c in all_candidates if c.id not in final_ids]

    def serialize_route(r):
        return {
            "backend_name": r.inference_backend.name,
            "backend_type": r.inference_backend.provider,
            "priority": r.priority,
            "weight": r.weight,
            "state": r.state,
        }

    return RoutingExplainResponse(
        requested_model=payload.model,
        resolved_model_id=str(selected_model.model_id),
        resolved_model_alias=selected_model.model_alias,
        client_name=client.name,
        plan_code=client.billing_plan.code if client.billing_plan else "free",
        routing_policy=routing_policy,
        chosen_backend=final_candidates[0].inference_backend.name if final_candidates else None,
        candidates_order=[serialize_route(c) for c in final_candidates],
        rejected_candidates=[serialize_route(c) for c in rejected],
    )


@router.post("/models/reload", response_model=ModelReloadResponse)
async def reload_models(
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    await ensure_default_model(session)
    await session.commit()
    await proxy.health()
    return ModelReloadResponse(
        status="accepted",
        detail="registry reloaded from configuration; for a new GGUF file, restart the data-plane container",
    )
