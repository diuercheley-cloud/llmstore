# Owner: platform-ops
from app.schemas.routing import (
    CommercialSimulateRequest,
    CommercialSimulateResponse,
    LastDecisionRead,
    PolicyRead,
    SimulateRoutingRequest,
    SimulateRoutingResponse,
    SmartRouterInput,
)
from app.services.auth import require_admin
from app.services.routing.commercial_routing import simulate_commercial_routing
from app.services.routing.smart_router import SmartRouter, get_smart_router
from fastapi import APIRouter, Depends, Query

router = APIRouter(
    prefix="/admin/routing",
    tags=["admin", "routing"],
    dependencies=[Depends(require_admin)],
)


from app.services.runtime_dependencies import get_db_session
from app.services.routing.commercial_config_store import CommercialConfigStore
from sqlalchemy.ext.asyncio import AsyncSession


@router.post("/simulate", response_model=SimulateRoutingResponse)
async def simulate_routing(
    req: SimulateRoutingRequest,
    smart_router: SmartRouter = Depends(get_smart_router),
    db: AsyncSession = Depends(get_db_session),
):
    inp = SmartRouterInput(
        tenant=req.tenant,
        client_id=req.client_id,
        endpoint_type=req.endpoint_type,
        requested_model=req.requested_model,
        task_type=req.task_type,
        prompt_estimated_tokens=req.prompt_estimated_tokens,
        max_output_tokens=req.max_output_tokens,
        plan=req.plan,
        remaining_quota=req.remaining_quota,
        wallet_balance_brl=req.wallet_balance_brl,
        cloud_allowed=req.cloud_allowed,
        latency_preference=req.latency_preference,
        budget_preference=req.budget_preference,
        strategy=req.strategy,
    )
    
    store = CommercialConfigStore(db)
    dynamic_configs = await store.list_configs(active_only=True)
    
    decision, strategies, provider_states, config_snapshot = smart_router.simulate(inp, dynamic_configs=dynamic_configs)
    return SimulateRoutingResponse(
        decision=decision,
        strategies_considered=strategies,
        provider_states=provider_states,
        config_snapshot=config_snapshot,
    )


@router.get("/policies", response_model=PolicyRead)
async def get_routing_policies(
    smart_router: SmartRouter = Depends(get_smart_router),
):
    policy = smart_router.get_policy()
    return PolicyRead(
        default_strategy=policy.get("default_strategy", "local_first"),
        allow_cloud_fallback=policy.get("allow_cloud_fallback", False),
        complexity_threshold=policy.get("complexity_threshold", 4000),
        coding_provider_preference=policy.get("coding_provider_preference", "anthropic"),
        low_budget_provider_preference=policy.get("low_budget_provider_preference", "deepseek"),
        premium_provider_preference=policy.get("premium_provider_preference", "openai"),
        max_provider_cost_per_request_brl=policy.get("max_provider_cost_per_request_brl", 0.50),
        tenant_policy_overrides=policy.get("tenant_policy_overrides", {}),
        fallback_order=policy.get("fallback_order", ["local", "lmstudio", "mock"]),
    )


@router.get("/last-decisions", response_model=list[LastDecisionRead])
async def get_last_decisions(
    limit: int = Query(default=50, ge=1, le=200),
    smart_router: SmartRouter = Depends(get_smart_router),
):
    from datetime import datetime, UTC
    decisions = smart_router.get_last_decisions(limit=limit)
    result = []
    for d in decisions:
        ts = d.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                ts = datetime.now(UTC)
        result.append(LastDecisionRead(
            id=d.get("id", ""),
            timestamp=ts,
            requested_model=d.get("requested_model", ""),
            resolved_model=d.get("resolved_model", ""),
            selected_provider=d.get("selected_provider", ""),
            routing_strategy=d.get("routing_strategy", ""),
            fallback_used=d.get("fallback_used", False),
            fallback_reason=d.get("fallback_reason"),
            cloud_used=d.get("cloud_used", False),
            estimated_cost_brl=d.get("estimated_cost_brl", 0.0),
            sanitized_reason=d.get("sanitized_reason", ""),
        ))
    return result


@router.post("/commercial/simulate", response_model=CommercialSimulateResponse)
async def commercial_routing_simulate(
    req: CommercialSimulateRequest,
):
    return simulate_commercial_routing(req)
