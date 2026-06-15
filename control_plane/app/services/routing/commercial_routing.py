from __future__ import annotations

import logging
from typing import Any

from app.schemas.routing import (
    CommercialRouteCandidate,
    CommercialScoreExplained,
    CommercialSimulateRequest,
    CommercialSimulateResponse,
    RoutingStrategy,
    TaskType,
)
from app.services.billing.pricing_engine import (
    calculate_customer_price,
    calculate_margin,
    estimate_provider_cost,
)
from app.services.billing.revenue_protection import get_active_revenue_protection_constraints
from app.services.routing.smart_router import (
    CLOUD_PROVIDERS,
    _get_cloud_providers_enabled,
    _is_provider_available,
)

logger = logging.getLogger(__name__)

ALL_PROVIDERS = ["local", "lmstudio", "deepseek", "openai", "anthropic", "openrouter", "mock"]

PROVIDER_TIER_MAP: dict[str, str] = {
    "local": "local",
    "lmstudio": "local",
    "mock": "local",
    "deepseek": "budget",
    "openai": "premium",
    "anthropic": "premium",
    "openrouter": "premium",
}

CODING_PROVIDER_ORDER = [
    "anthropic",
    "openai",
    "deepseek",
    "local",
    "lmstudio",
    "openrouter",
    "mock",
]
LOW_COST_ORDER = ["deepseek", "local", "lmstudio", "openai", "anthropic", "openrouter", "mock"]
PREMIUM_ORDER = ["openai", "anthropic", "local", "lmstudio", "deepseek", "openrouter", "mock"]
LOCAL_FIRST_ORDER = ["local", "lmstudio", "deepseek", "openai", "anthropic", "openrouter", "mock"]
DEFAULT_CODING_PROVIDER = "anthropic"


def _get_customer_pricing_config() -> dict[str, Any]:
    from app.services.billing.pricing_engine import _get_customer_pricing

    return _get_customer_pricing()


def _get_plan_config(plan: str) -> dict[str, Any]:
    pricing = _get_customer_pricing_config()
    plans = pricing.get("plans", {})
    return plans.get(plan, {})


def _get_commercial_routing_config() -> dict[str, Any]:
    pricing = _get_customer_pricing_config()
    return pricing.get("commercial_routing", {})


def _estimate_price_brl(plan_code: str, prompt_tokens: int, completion_tokens: int) -> float:
    result = calculate_customer_price(plan_code, prompt_tokens, completion_tokens)
    return result.price_brl


def _determine_tier(
    plan: str, task_type: TaskType, billing_status: str, wallet_balance: float | None
) -> str:
    if billing_status in ("suspended", "blocked", "overdue"):
        return "suspended"
    if wallet_balance is not None and wallet_balance <= _get_commercial_routing_config().get(
        "low_balance_threshold_brl", 5.0
    ):
        return "low_balance"
    tier_map = {
        "free": "basic",
        "basic": "basic",
        "pro": "pro",
        "enterprise": "premium",
    }
    base_tier = tier_map.get(plan, "basic")
    if task_type == TaskType.coding:
        return "coding"
    return base_tier


def _get_providers_for_tier(tier: str, cloud_allowed: bool) -> list[str]:
    if not cloud_allowed:
        return ["local", "lmstudio", "mock"]
    order_map = {
        "basic": LOCAL_FIRST_ORDER,
        "pro": LOW_COST_ORDER,
        "premium": PREMIUM_ORDER,
        "coding": CODING_PROVIDER_ORDER,
        "suspended": ["local", "lmstudio", "mock"],
        "low_balance": LOW_COST_ORDER,
    }
    return order_map.get(tier, LOCAL_FIRST_ORDER)


def _get_strategy_for_tier(tier: str) -> RoutingStrategy:
    strategy_map = {
        "basic": RoutingStrategy.local_first,
        "pro": RoutingStrategy.lowest_cost,
        "premium": RoutingStrategy.premium_quality,
        "coding": RoutingStrategy.coding,
        "suspended": RoutingStrategy.local_first,
        "low_balance": RoutingStrategy.local_first,
    }
    return strategy_map.get(tier, RoutingStrategy.local_first)


def _is_provider_healthy(provider_id: str) -> bool:
    from app.services.routing.smart_router import _provider_health

    state = _provider_health(provider_id)
    return state in ("healthy", "unknown_async", "unregistered")


def _evaluate_candidate(
    provider: str,
    model: str,
    plan: str,
    prompt_tokens: int,
    completion_tokens: int,
    tier: str,
    plan_cfg: dict[str, Any],
    wallet_balance: float | None,
    constraints: dict[str, Any] | None = None,
) -> CommercialRouteCandidate:
    cost_result = estimate_provider_cost(provider, prompt_tokens, completion_tokens)
    cost_brl = cost_result.cost_brl

    price_brl = _estimate_price_brl(plan, prompt_tokens, completion_tokens)

    margin = calculate_margin(cost_brl, price_brl)

    is_cloud = provider in CLOUD_PROVIDERS
    reasons: list[str] = []

    max_cost = plan_cfg.get("max_cost_per_request_brl")
    commercial_cfg = _get_commercial_routing_config()
    if max_cost is None:
        max_cost = commercial_cfg.get("default_max_cost_per_request_brl", 0.50)
    if constraints and constraints.get("max_cost_override") is not None:
        max_cost = min(float(max_cost), float(constraints["max_cost_override"]))

    if cost_brl > max_cost:
        reasons.append(f"cost {cost_brl:.6f} exceeds max_cost_per_request_brl {max_cost}")
    if constraints:
        restricted_models = set(constraints.get("restricted_models") or [])
        if model in restricted_models:
            reasons.append("model restricted by revenue protection")
        if constraints.get("force_local_only") and is_cloud:
            reasons.append("force_local_only active")
        if constraints.get("require_approval") and is_cloud:
            reasons.append("manual approval required for expensive action")

    if tier == "suspended" and is_cloud:
        reasons.append("client suspended; cloud providers blocked")

    if tier == "low_balance":
        if is_cloud and wallet_balance is not None and wallet_balance <= 0:
            reasons.append(f"wallet balance {wallet_balance} too low for cloud provider")
        if cost_brl > (wallet_balance or 0):
            reasons.append(f"cost {cost_brl:.6f} exceeds wallet balance {wallet_balance or 0}")

    if tier in ("basic", "pro", "premium"):
        min_margin = plan_cfg.get(
            "minimum_margin_percent", commercial_cfg.get("default_minimum_margin_percent", 5.0)
        )
        if margin.margin_percent is not None and margin.margin_percent < min_margin and is_cloud:
            reasons.append(f"margin {margin.margin_percent:.2f}% below minimum {min_margin}%")

    if not _is_provider_available(provider):
        reasons.append("provider not available or not configured")
    elif not _is_provider_healthy(provider):
        reasons.append("provider unhealthy")

    rejected = len(reasons) > 0

    return CommercialRouteCandidate(
        provider=provider,
        model=model,
        estimated_cost_brl=round(cost_brl, 8),
        estimated_price_brl=round(price_brl, 8),
        estimated_margin_brl=round(margin.gross_profit_brl, 8),
        estimated_margin_percent=round(margin.margin_percent, 4)
        if margin.margin_percent is not None
        else None,
        is_cloud=is_cloud,
        rejected=rejected,
        rejection_reason="; ".join(reasons) if reasons else None,
    )


def _select_by_tier(
    candidates: list[CommercialRouteCandidate],
    tier: str,
    plan_cfg: dict[str, Any],
    wallet_balance: float | None,
) -> CommercialRouteCandidate | None:
    if tier == "coding":
        preferred = DEFAULT_CODING_PROVIDER
        for c in candidates:
            if c.provider == preferred and not c.rejected:
                return c
        for c in candidates:
            if not c.rejected:
                return c
        return None

    if tier == "pro":
        for c in candidates:
            if not c.rejected:
                return c
        return None

    if tier == "basic":
        for c in candidates:
            if not c.rejected:
                return c
        return None

    if tier == "premium":
        for c in candidates:
            if not c.rejected:
                return c
        return None

    if tier == "suspended":
        for c in candidates:
            if not c.rejected and not c.is_cloud:
                return c
        return None

    if tier == "low_balance":
        for c in candidates:
            if not c.rejected:
                return c
        return None

    for c in candidates:
        if not c.rejected:
            return c
    return None


def _candidate_to_explained(c: CommercialRouteCandidate) -> CommercialScoreExplained:
    return CommercialScoreExplained(
        provider=c.provider,
        model=c.model,
        score=0.0,
        estimated_cost_brl=c.estimated_cost_brl,
        estimated_revenue_brl=c.estimated_price_brl,
        estimated_margin_brl=c.estimated_margin_brl,
        estimated_margin_percent=c.estimated_margin_percent,
        rejection_reasons=[c.rejection_reason] if c.rejection_reason else [],
    )


def simulate_commercial_routing(req: CommercialSimulateRequest) -> CommercialSimulateResponse:
    plan_cfg = _get_plan_config(req.plan)

    plan_cloud_allowed = plan_cfg.get("cloud_allowed", False)
    cloud_allowed = req.cloud_allowed if req.cloud_allowed is not None else plan_cloud_allowed
    cloud_enabled_globally = _get_cloud_providers_enabled()
    effective_cloud_allowed = cloud_allowed and cloud_enabled_globally

    tier = _determine_tier(req.plan, req.task_type, req.billing_status, req.wallet_balance_brl)
    constraints = get_active_revenue_protection_constraints(
        client_id=req.client_id, model=req.model, qos_tier=tier
    )
    if constraints.get("force_local_only"):
        effective_cloud_allowed = False
    if constraints.get("qos_priority_override") == "reduced" and tier not in {
        "suspended",
        "low_balance",
    }:
        tier = "basic"

    provider_order = _get_providers_for_tier(tier, effective_cloud_allowed)

    strategy = _get_strategy_for_tier(tier)

    candidates: list[CommercialRouteCandidate] = []
    for provider in provider_order:
        model = f"{provider}-model"
        if provider == "mock":
            model = "mock-model"
        candidate = _evaluate_candidate(
            provider=provider,
            model=model,
            plan=req.plan,
            prompt_tokens=req.estimated_input_tokens,
            completion_tokens=req.estimated_output_tokens,
            tier=tier,
            plan_cfg=plan_cfg,
            wallet_balance=req.wallet_balance_brl,
            constraints=constraints,
        )
        candidates.append(candidate)

    selected = _select_by_tier(candidates, tier, plan_cfg, req.wallet_balance_brl)

    rejected_routes = [_candidate_to_explained(c) for c in candidates if c != selected]

    if selected:
        ranked = [_candidate_to_explained(selected)]
        explanation = f"{tier} tier: selected {selected.provider} via {strategy.value}"
        if constraints.get("force_local_only"):
            explanation += "; force_local_only active"
        if constraints.get("require_approval"):
            explanation += "; require_approval active"
    else:
        ranked = []
        all_rejected = [c for c in candidates if c.rejected]
        reject_reasons = list(set(c.rejection_reason for c in all_rejected if c.rejection_reason))
        explanation = "no profitable or permitted route found"
        if reject_reasons:
            explanation += ": " + "; ".join(reject_reasons)

    return CommercialSimulateResponse(
        selected_route=ranked[0] if ranked else None,
        ranked_routes=ranked,
        rejected_routes=rejected_routes,
        explanation=explanation,
        tier=tier,
    )
