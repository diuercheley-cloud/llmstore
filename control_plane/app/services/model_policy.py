import json
import random

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry


SUPPORTED_BACKENDS = {"llama.cpp", "ollama", "vllm"}
ROUTE_STATE_ORDER = {"healthy": 0, "degraded": 1, "unhealthy": 2, "disabled": 3}


def _parse_allowed_models(raw: str | None) -> set[str]:
    if not raw:
        return set()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {str(item) for item in parsed if str(item).strip()}


def get_effective_allowed_models(client: Client) -> set[str]:
    client_allowed = _parse_allowed_models(client.allowed_models_json)
    if client_allowed:
        return client_allowed
    if client.billing_plan is None:
        return set()
    return _parse_allowed_models(client.billing_plan.allowed_models_json)


async def list_active_registry_models(session: AsyncSession) -> list[ModelRegistry]:
    result = await session.execute(
        select(ModelRegistry)
        .options(
            selectinload(ModelRegistry.inference_backend),
            selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
        )
        .where(ModelRegistry.is_active.is_(True))
        .order_by(ModelRegistry.is_default.desc(), ModelRegistry.created_at.asc())
    )
    return [
        item
        for item in result.scalars().all()
        if item.inference_backend is None or item.inference_backend.is_active
    ]


async def resolve_requested_model(
    session: AsyncSession,
    *,
    client: Client,
    requested_model: str,
) -> tuple[ModelRegistry, str]:
    active_models = await list_active_registry_models(session)
    if not active_models:
        raise HTTPException(status_code=503, detail="no active models configured")

    selected = next(
        (
            item
            for item in active_models
            if item.model_id == requested_model or item.model_alias == requested_model
        ),
        None,
    )
    if selected is None and requested_model in {"", "default"}:
        selected = next((item for item in active_models if item.is_default), None) or active_models[0]
    if selected is None:
        raise HTTPException(status_code=404, detail="requested model not found")
    routes = get_routing_candidates(selected)
    if not routes:
        raise HTTPException(status_code=503, detail="model backend is not active")

    allowed = get_effective_allowed_models(client)
    if allowed and selected.model_id not in allowed and (selected.model_alias or "") not in allowed:
        raise HTTPException(status_code=403, detail="requested model is not allowed for this client")
    return selected, requested_model


def get_routing_candidates(model: ModelRegistry) -> list[ModelBackendRoute]:
    routes = [
        item
        for item in model.backend_routes
        if item.inference_backend is not None and item.inference_backend.is_active and item.state != "disabled"
    ]
    if not routes and model.inference_backend is not None and model.inference_backend.is_active:
        synthetic = ModelBackendRoute(
            model_registry_id=model.id,
            inference_backend_id=model.inference_backend.id,
            priority=1,
            weight=100,
            state="healthy",
        )
        synthetic.inference_backend = model.inference_backend
        return [synthetic]
    return sorted(
        routes,
        key=lambda item: (
            ROUTE_STATE_ORDER.get(item.state, 99),
            item.priority,
            -item.weight,
            item.created_at,
        ),
    )


def plan_routing_order(model: ModelRegistry, rng: random.Random | None = None) -> list[ModelBackendRoute]:
    routes = get_routing_candidates(model)
    if len(routes) <= 1:
        return routes

    rng = rng or random.Random()
    grouped: dict[tuple[int, int], list[ModelBackendRoute]] = {}
    for route in routes:
        key = (ROUTE_STATE_ORDER.get(route.state, 99), route.priority)
        grouped.setdefault(key, []).append(route)

    ordered: list[ModelBackendRoute] = []
    for key in sorted(grouped):
        bucket = list(grouped[key])
        while bucket:
            if len(bucket) == 1:
                ordered.append(bucket.pop(0))
                continue
            weights = [max(item.weight, 1) for item in bucket]
            chosen = rng.choices(bucket, weights=weights, k=1)[0]
            ordered.append(chosen)
            bucket.remove(chosen)
    return ordered


def serialize_routing_table(model: ModelRegistry) -> list[dict]:
    return [
        {
            "route_id": str(route.id) if route.id else None,
            "backend_id": str(route.inference_backend_id),
            "backend_name": route.inference_backend.name if route.inference_backend else None,
            "backend_url": route.inference_backend.backend_url if route.inference_backend else None,
            "provider": route.inference_backend.provider if route.inference_backend else None,
            "priority": route.priority,
            "weight": route.weight,
            "state": route.state,
        }
        for route in plan_routing_order(model, random.Random(0))
    ]


def serialize_model_card(item: ModelRegistry) -> dict:
    metadata = {}
    if item.metadata_json:
        try:
            metadata = json.loads(item.metadata_json)
        except json.JSONDecodeError:
            metadata = {"raw_metadata": item.metadata_json}
    return {
        "id": item.model_alias or item.model_id,
        "object": "model",
        "owned_by": item.provider,
        "metadata": {
            **metadata,
            "model_id": item.model_id,
            "model_alias": item.model_alias,
            "provider": item.provider,
            "context_length": item.context_length,
            "is_default": item.is_default,
        },
    }


async def get_model_by_id(session: AsyncSession, model_id) -> ModelRegistry | None:
    return await session.get(ModelRegistry, model_id)


async def find_model_by_public_name(session: AsyncSession, public_name: str) -> ModelRegistry | None:
    result = await session.execute(
        select(ModelRegistry)
        .options(
            selectinload(ModelRegistry.inference_backend),
            selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
        )
        .where(
            or_(ModelRegistry.model_id == public_name, ModelRegistry.model_alias == public_name)
        )
    )
    return result.scalar_one_or_none()
