from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.schemas.routing import (
    CommercialScoreExplained,
    TaskType,
)
from app.services.billing.pricing_engine import (
    calculate_customer_price,
    calculate_margin,
    estimate_provider_cost,
)
from app.services.provider_classification import is_cloud_provider, is_local_provider
from app.services.routing.smart_router import _is_provider_available, _provider_health

logger = logging.getLogger(__name__)

# Mock latency data (in a real system this would come from monitoring or historical logs)
MOCK_LATENCY = {
    "local": 50,
    "lmstudio": 100,
    "mock": 10,
    "deepseek": 300,
    "openai": 450,
    "anthropic": 500,
    "openrouter": 700,
}

# Quality scores (0-100) - represents model capabilities
PROVIDER_QUALITY = {
    "openai": 95,
    "anthropic": 98,
    "deepseek": 88,
    "local": 70,
    "lmstudio": 75,
    "openrouter": 90,
    "mock": 10,
}



def rank_commercial_routes(
    candidates: list[dict[str, Any]],
    client_plan: str,
    task_type: TaskType,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    wallet_balance: float | None = None,
    billing_status: str = "active",
    dynamic_configs: list[Any] | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    client_id: str | None = None,
    qos_tier: Any | None = None,
) -> tuple[list[CommercialScoreExplained], list[CommercialScoreExplained], list[dict[str, Any]]]:
    """
    Ranks routing candidates based on commercial metrics.
    Returns (ranked_routes, rejected_routes, guardrail_decisions).
    """
    from app.services.routing.commercial_auto_apply import CommercialAutoApplyService
    from app.services.routing.commercial_qos import CommercialQoSService
    
    settings = get_settings()
    ranked: list[CommercialScoreExplained] = []
    rejected: list[CommercialScoreExplained] = []
    guardrail_decisions: list[dict[str, Any]] = []

    for cand in candidates:
        provider = cand["provider"]
        model = cand.get("model", f"{provider}-model")
        
        # Get dynamic config from the passed list (specificity: provider_model > model > provider > global)
        eff_config = {
            "cost_multiplier": 1.0,
            "margin_weight": settings.commercial_margin_weight,
            "latency_weight": settings.commercial_latency_weight,
            "quality_weight": settings.commercial_quality_weight,
            "local_route_bonus": settings.commercial_local_route_bonus,
            "min_margin_percent": settings.commercial_min_margin_percent,
            "source": "default"
        }

        if dynamic_configs:
            def sort_key(c):
                st = getattr(c, "scope_type", None)
                if st is None and isinstance(c, dict):
                    st = c.get("scope_type", "")
                return {
                    "provider_model": 1,
                    "model": 2,
                    "provider": 3,
                    "global": 4
                }.get(st or "", 5)
            
            # Simple matching for Phase 7
            matches = []
            for dc in dynamic_configs:
                def get_attr(obj, attr):
                    if hasattr(obj, attr):
                        return getattr(obj, attr)
                    if isinstance(obj, dict):
                        return obj.get(attr)
                    return None

                st = get_attr(dc, "scope_type")
                p = get_attr(dc, "provider")
                m = get_attr(dc, "model")
                
                if st == "provider_model" and p == provider and m == model:
                    matches.append(dc)
                elif st == "model" and m == model:
                    matches.append(dc)
                elif st == "provider" and p == provider:
                    matches.append(dc)
                elif st == "global":
                    matches.append(dc)
            
            if matches:
                matches.sort(key=lambda x: (sort_key(x), -getattr(x, "canary_enabled", False), -getattr(x, "created_at", datetime.now(timezone.utc)).timestamp()))
                
                # Filter by specificity and handle canary
                # Group by specificity
                best_by_scope = {}
                for m in matches:
                    st = getattr(m, "scope_type", "global")
                    if st not in best_by_scope:
                        best_by_scope[st] = []
                    best_by_scope[st].append(m)
                
                # Pick most specific scope that has configs
                best_scope = "global"
                for st in ["provider_model", "model", "provider", "global"]:
                    if st in best_by_scope:
                        best_scope = st
                        break
                
                configs_for_scope = best_by_scope.get(best_scope, [])
                
                # Within this scope, find best stable and best canary
                canary_config = next((c for c in configs_for_scope if getattr(c, "canary_enabled", False)), None)
                stable_config = next((c for c in configs_for_scope if not getattr(c, "canary_enabled", False)), None)
                
                best = stable_config
                variant = "stable" if stable_config else "default"
                if canary_config:
                    bucket = CommercialAutoApplyService.get_canary_bucket(request_id, correlation_id, client_id)
                    if bucket < getattr(canary_config, "canary_percent", 0):
                        best = canary_config
                        variant = "canary"
                    elif not stable_config:
                        # If no stable config for this specific scope, fallback to next level
                        # For now let's just use what we have or next best in matches
                        best = next((c for c in matches if not getattr(c, "canary_enabled", False)), None)
                        variant = "stable" if best else "default"

                if best:
                    eff_config.update({
                        "id": getattr(best, "id", None),
                        "variant": variant,
                        "cost_multiplier": get_attr(best, "cost_multiplier") if get_attr(best, "cost_multiplier") is not None else 1.0,
                        "margin_weight": get_attr(best, "margin_weight") if get_attr(best, "margin_weight") is not None else 0.6,
                        "latency_weight": get_attr(best, "latency_weight") if get_attr(best, "latency_weight") is not None else 0.2,
                        "quality_weight": get_attr(best, "quality_weight") if get_attr(best, "quality_weight") is not None else 0.2,
                        "local_route_bonus": get_attr(best, "local_route_bonus") if get_attr(best, "local_route_bonus") is not None else 20.0,
                        "min_margin_percent": get_attr(best, "min_margin_percent") if get_attr(best, "min_margin_percent") is not None else 10.0,
                        "source": get_attr(best, "source") or "manual"
                    })

        is_cloud = is_cloud_provider(provider)
        rejection_reasons = []
        
        # 1. Availability and Health Checks
        if not _is_provider_available(provider):
            rejection_reasons.append("provider_not_configured_or_disabled")
        
        health = _provider_health(provider)
        if health not in ("healthy", "unknown_async"):
            rejection_reasons.append(f"provider_unhealthy_{health}")

        # 2. Global Guardrails
        if is_cloud and settings.global_cloud_kill_switch:
            rejection_reasons.append("global_cloud_kill_switch_active")

        # 3. Client Status
        if is_cloud and billing_status in ("suspended", "overdue", "blocked"):
            rejection_reasons.append(f"client_billing_status_{billing_status}")

        # 4. Financial Calculations
        # Apply cost multiplier from dynamic config
        cost_res = estimate_provider_cost(provider, estimated_input_tokens, estimated_output_tokens)
        adjusted_cost_brl = cost_res.cost_brl * eff_config["cost_multiplier"]
        
        price_res = calculate_customer_price(client_plan, estimated_input_tokens, estimated_output_tokens)
        margin_res = calculate_margin(adjusted_cost_brl, price_res.price_brl)
        
        # Margin Check
        min_margin = eff_config["min_margin_percent"]
        if is_cloud and margin_res.margin_percent is not None and margin_res.margin_percent < min_margin:
            rejection_reasons.append(f"margin_below_minimum_{margin_res.margin_percent:.1f}%")

        # Wallet Balance Check
        if is_cloud and wallet_balance is not None and wallet_balance < adjusted_cost_brl:
             rejection_reasons.append(f"insufficient_wallet_balance_{wallet_balance:.2f}_needed_{adjusted_cost_brl:.2f}")

        # QoS Tier Enforcement (Phase 20)
        if qos_tier:
            current_p95 = MOCK_LATENCY.get(provider, 1000)
            qos_pass, qos_reasons = CommercialQoSService.evaluate_route_against_qos(
                tier=qos_tier,
                candidate=cand,
                estimated_margin_percent=margin_res.margin_percent,
                estimated_cost_brl=adjusted_cost_brl,
                is_cloud=is_cloud,
                current_p95_latency=current_p95
            )
            if not qos_pass:
                rejection_reasons.extend(qos_reasons)

        # 5. Score Calculation
        
        # Margin Score (0-100)
        margin_score = min(100, max(0, (margin_res.margin_percent or 0) * 1.5)) 
        
        # Latency Penalty
        latency = MOCK_LATENCY.get(provider, 1000)
        latency_penalty = min(50, latency / 20.0)
        
        # Quality score
        quality_score = PROVIDER_QUALITY.get(provider, 50)
        
        # Task specific quality bonus
        if task_type == TaskType.coding and provider in ("anthropic", "openai"):
            quality_score = 100
            
        health_penalty = 0
        if health == "degraded":
            health_penalty = 30
            
        local_bonus = eff_config["local_route_bonus"] if is_local_provider(provider) else 0
        
        # Plan-specific Policy Bonus
        policy_bonus = 0
        if client_plan == "basic" and is_local_provider(provider):
            policy_bonus = 20
        elif client_plan == "pro" and margin_res.margin_percent and margin_res.margin_percent > 40:
            policy_bonus = 15
        elif client_plan == "premium" and quality_score >= 95:
            policy_bonus = 25
        elif client_plan == "coding" and task_type == TaskType.coding and provider == "anthropic":
            policy_bonus = 30

        # Weights from dynamic config
        w_margin = eff_config["margin_weight"]
        w_latency = eff_config["latency_weight"]
        w_quality = eff_config["quality_weight"]
        
        weighted_score = (margin_score * w_margin) + (quality_score * w_quality) - (latency_penalty * w_latency)
        final_score = weighted_score + local_bonus + policy_bonus - health_penalty
        
        explanation = CommercialScoreExplained(
            provider=provider,
            model=model,
            score=round(final_score, 2),
            estimated_cost_brl=adjusted_cost_brl,
            estimated_revenue_brl=price_res.price_brl,
            estimated_margin_brl=margin_res.gross_profit_brl,
            estimated_margin_percent=margin_res.margin_percent,
            latency_penalty=round(latency_penalty, 2),
            health_penalty=health_penalty,
            local_bonus=local_bonus,
            policy_bonus=policy_bonus,
            rejection_reasons=rejection_reasons,
            commercial_config_id=eff_config.get("id"),
            commercial_config_variant=eff_config.get("variant"),
        )
        
        if rejection_reasons:
            rejected.append(explanation)
            logger.debug(
                "commercial_route_rejected: provider=%s reasons=%s",
                provider, ", ".join(rejection_reasons)
            )
        else:
            ranked.append(explanation)
            logger.debug(
                "commercial_route_ranked: provider=%s score=%.2f",
                provider, explanation.score
            )

    # Final sorting: score descending
    ranked.sort(key=lambda x: x.score, reverse=True)
    
    # Log the selection if something was ranked
    if ranked:
        top = ranked[0]
        logger.info(
            "commercial_route_selected: provider=%s model=%s score=%.2f margin=%.1f%%",
            top.provider, top.model, top.score, top.estimated_margin_percent or 0
        )
    
    return ranked, rejected, guardrail_decisions
