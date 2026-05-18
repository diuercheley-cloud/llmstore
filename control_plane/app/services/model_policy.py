import json
import random
from typing import Any

from fastapi import HTTPException
from sqlalchemy import inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.client import Client
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.billing.revenue_protection import get_active_revenue_protection_constraints
from app.services.commercial_guardrails import filter_routes_by_commercial_guardrails
from app.services.models.signed_model_registry import enforce_model_trust_or_warn
from app.services.provider_classification import is_cloud_provider
from app.utils.tool_calling import provider_supports_native_tools


SUPPORTED_BACKENDS = {"llama.cpp", "ollama", "vllm"}
ROUTE_STATE_ORDER = {"healthy": 0, "degraded": 1, "unhealthy": 2, "disabled": 3}
MODEL_REGISTRY_ROUTING_LOADS = (
    selectinload(ModelRegistry.inference_backend),
    selectinload(ModelRegistry.backend_routes).selectinload(ModelBackendRoute.inference_backend),
)


async def get_usable_chat_model(session: AsyncSession) -> tuple[dict | None, str | None]:
    """
    Finds the best usable chat model.
    Prioritizes default models and requires chat capability.
    Accepts unhealthy backends if mock fallback is enabled.
    """
    models = await list_active_registry_models(session)
    if not models:
        return None, "no_models_registered"

    cards = [serialize_model_card(m) for m in models]
    
    # Filter for chat models
    chat_models = [c for c in cards if c["capabilities"]["chat"]]
    if not chat_models:
        return None, "no_chat_models_registered"
        
    # Find first ready (prioritizes default due to list_active_registry_models order)
    for card in chat_models:
        if card["local_ready"]:
            return card, None
            
    # None ready, return reason from the first chat model (likely the default one)
    return None, chat_models[0].get("reason") or "no_ready_chat_model"


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
        .options(*MODEL_REGISTRY_ROUTING_LOADS)
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
    await enforce_model_trust_or_warn(
        session,
        model_name=selected.model_alias or selected.model_id,
        client=client,
    )
    constraints = get_active_revenue_protection_constraints(client_id=client.id, model=selected.model_id)
    restricted_models = set(constraints.get("restricted_models") or [])
    if selected.model_id in restricted_models or (selected.model_alias or "") in restricted_models:
        fallback = next(
            (
                item
                for item in active_models
                if item.model_id not in restricted_models and (item.model_alias or "") not in restricted_models
            ),
            None,
        )
        if fallback is None:
            raise HTTPException(status_code=403, detail="requested model restricted by revenue protection")
        selected = fallback
    routes = get_routing_candidates(selected)
    if not routes:
        raise HTTPException(status_code=503, detail="model backend is not active")

    allowed = get_effective_allowed_models(client)
    if allowed and selected.model_id not in allowed and (selected.model_alias or "") not in allowed:
        # Rewrite to default model instead of 403
        selected = next((item for item in active_models if item.is_default), None) or active_models[0]
        # Re-verify that the default model has routes
        routes = get_routing_candidates(selected)
        if not routes:
            raise HTTPException(status_code=503, detail="default model backend is not active")
            
    return selected, requested_model


def get_routing_candidates(model: ModelRegistry) -> list[ModelBackendRoute]:
    ensure_model_routing_loaded(model, require_primary_backend=False)
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


def apply_routing_policy(
    model: ModelRegistry, 
    client: Client | None, 
    candidates: list[ModelBackendRoute],
    qos_tier: Any | None = None,
) -> list[ModelBackendRoute]:
    """
    Applies global routing policies from the client's billing plan to the candidates.
    """
    from app.services.provider_classification import is_cloud_provider
    
    # Phase 20: QoS Tier Enforcement
    if qos_tier:
        if not qos_tier.allow_cloud:
            candidates = [c for c in candidates if not is_cloud_provider(c.inference_backend.provider)]
        
        # Check if we should allow degraded based on QoS
        if not qos_tier.allow_degraded_cluster:
            candidates = [c for c in candidates if c.state == "healthy"]

    constraints = get_active_revenue_protection_constraints(
        client_id=getattr(client, "id", None),
        model=model.model_id if model else None,
        qos_tier=getattr(qos_tier, "name", None),
    )
    if constraints.get("force_local_only"):
        candidates = [c for c in candidates if not is_cloud_provider(c.inference_backend.provider)]
    restricted_models = set(constraints.get("restricted_models") or [])
    if model.model_id in restricted_models or (model.model_alias or "") in restricted_models:
        return []

    if not client or not client.billing_plan or not client.billing_plan.routing_policy_json:
        return candidates
        
    try:
        policy = json.loads(client.billing_plan.routing_policy_json)
    except json.JSONDecodeError:
        return candidates
        
    rules = policy.get("rules", [])
    if not rules:
        return candidates
        
    for rule in rules:
        action = rule.get("action")
        value = rule.get("value")
        
        if action == "exclude_backend_type":
            candidates = [c for c in candidates if c.inference_backend.provider != value]
        elif action == "exclude_backend":
            candidates = [c for c in candidates if c.inference_backend.name != value]
        elif action == "prioritize_backend_type":
            boost = rule.get("priority_boost", 10)
            for c in candidates:
                if c.inference_backend.provider == value:
                    c.priority -= boost
        elif action == "prioritize_backend":
            boost = rule.get("priority_boost", 10)
            for c in candidates:
                if c.inference_backend.name == value:
                    c.priority -= boost
                    
    # Re-sort candidates after applying priority boosts or exclusions
    return sorted(
        candidates,
        key=lambda item: (
            ROUTE_STATE_ORDER.get(item.state, 99),
            item.priority,
            -item.weight,
            item.created_at,
        ),
    )


def plan_routing_order(
    model: ModelRegistry, 
    rng: random.Random | None = None,
    client: Client | None = None,
    cloud_blocked_by_guardrail: bool = False,
    commercial_guardrail_context: dict | None = None,
    qos_tier: Any | None = None,
) -> list[ModelBackendRoute]:
    routes = get_routing_candidates(model)

    # Apply global policies from client plan
    if client:
        routes = apply_routing_policy(model, client, routes, qos_tier=qos_tier)

    # Legacy SaaS-only guardrail compatibility.
    if cloud_blocked_by_guardrail:
        routes = [r for r in routes if not is_cloud_provider(r.inference_backend.provider)]

    routes = filter_routes_by_commercial_guardrails(routes, commercial_guardrail_context)
        
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
    ensure_model_routing_loaded(model, require_primary_backend=False)
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
    settings = get_settings()
    metadata = {}
    if item.metadata_json:
        try:
            metadata = json.loads(item.metadata_json)
        except json.JSONDecodeError:
            metadata = {"raw_metadata": item.metadata_json}

    # Derive capabilities
    is_embedding = "embedding" in item.model_id.lower() or metadata.get("type") == "embedding"
    is_chat = not is_embedding and item.provider in {"llama.cpp", "ollama", "vllm", "openai_compatible", "openrouter", "openai", "anthropic", "deepseek"}
    
    capabilities = {
        "chat": is_chat,
        "streaming": is_chat,
        "embeddings": is_embedding,
        "responses": is_chat,
        "tools": is_chat and provider_supports_native_tools(item.provider),
    }

    # Backend status and routing
    routes = get_routing_candidates(item)
    backend_status = "unknown"
    if routes:
        backend_status = routes[0].state
    elif item.inference_backend_id:
        backend_status = "no_route"
    
    # Readiness logic
    is_ready = backend_status in {"healthy", "degraded"}
    
    # Accept mock if enabled or in local/test environment
    is_mock_env = settings.app_env in {"local", "test"}
    if not is_ready and (settings.mock_backend_enabled or is_mock_env):
        is_ready = True
        if backend_status == "unknown" or backend_status == "no_route":
            backend_status = "mock_fallback"

    reason = None
    if not is_ready:
        if not routes and not item.inference_backend_id:
            reason = "no_active_routes"
        else:
            reason = f"backend_{backend_status}"

    provider_info = None
    try:
        from app.services.providers.registry import get_provider
        for pid in ("local", "lmstudio", "openai", "anthropic", "deepseek"):
            prov = get_provider(pid)
            if prov and prov.enabled and prov.configured:
                caps = prov.capabilities()
                provider_info = {
                    "provider_id": prov.provider_id,
                    "provider_type": prov.provider_type.value,
                    "enabled": prov.enabled,
                    "configured": prov.configured,
                    "capabilities": caps.model_dump(),
                }
                break
    except Exception:
        pass

    return {
        "id": item.model_alias or item.model_id,
        "object": "model",
        "owned_by": item.provider,
        "capabilities": capabilities,
        "enabled": item.is_active,
        "backend_status": backend_status,
        "production_ready": is_ready and settings.app_env == "production",
        "local_ready": is_ready,
        "reason": reason,
        "metadata": {
            **metadata,
            "model_id": item.model_id,
            "model_alias": item.model_alias,
            "provider": item.provider,
            "context_length": item.context_length,
            "is_default": item.is_default,
        },
        "provider_info": provider_info,
    }


def ensure_model_routing_loaded(model: ModelRegistry, *, require_primary_backend: bool = True) -> None:
    state = inspect(model)
    unloaded = set(state.unloaded)
    missing = []
    if "backend_routes" in unloaded:
        missing.append("ModelRegistry.backend_routes")
    needs_primary_backend = require_primary_backend
    if not needs_primary_backend and not missing:
        needs_primary_backend = not model.backend_routes and model.inference_backend_id is not None
    if needs_primary_backend and "inference_backend" in unloaded:
        missing.append("ModelRegistry.inference_backend")
    if missing:
        raise RuntimeError(
            "ModelRegistry routing relationships must be eagerly loaded before serialization: "
            + ", ".join(missing)
        )
    for route in model.backend_routes:
        route_state = inspect(route)
        if "inference_backend" in route_state.unloaded:
            raise RuntimeError(
                "ModelBackendRoute.inference_backend must be eagerly loaded before routing serialization"
            )


async def get_model_by_id(session: AsyncSession, model_id) -> ModelRegistry | None:
    result = await session.execute(
        select(ModelRegistry)
        .options(*MODEL_REGISTRY_ROUTING_LOADS)
        .execution_options(populate_existing=True)
        .where(ModelRegistry.id == model_id)
    )
    return result.scalar_one_or_none()


async def find_model_by_public_name(session: AsyncSession, public_name: str) -> ModelRegistry | None:
    result = await session.execute(
        select(ModelRegistry)
        .options(*MODEL_REGISTRY_ROUTING_LOADS)
        .where(
            or_(ModelRegistry.model_id == public_name, ModelRegistry.model_alias == public_name)
        )
    )
    return result.scalar_one_or_none()
