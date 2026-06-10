from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.billing.request_financial import RequestFinancial
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_PROVIDER_PRICING_PATH = Path(__file__).resolve().parents[4] / "config" / "provider-pricing.example.json"
_CUSTOMER_PRICING_PATH = Path(__file__).resolve().parents[4] / "config" / "customer-pricing.example.json"


@dataclass
class ProviderCostResult:
    provider: str
    cost_usd: float
    cost_brl: float
    pricing_configured: bool
    fx_rate: float
    fx_rate_source: str
    details: dict[str, Any] | None = None


@dataclass
class CustomerPriceResult:
    price_brl: float
    plan_code: str | None
    markup_percent: float
    pricing_rule_id: str | None
    details: dict[str, Any] | None = None


@dataclass
class MarginResult:
    provider_cost_brl: float
    customer_price_brl: float
    gross_profit_brl: float
    margin_percent: float | None


@dataclass
class FinancialRecord:
    client_id: str
    endpoint_type: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cache_hit: bool
    latency_ms: int | None
    provider_cost_usd: float | None
    provider_cost_brl: float | None
    customer_price_brl: float | None
    gross_profit_brl: float | None
    margin_percent: float | None
    fx_rate: float
    fx_rate_source: str
    pricing_rule_id: str | None
    requested_model: str | None
    resolved_model: str | None
    api_key_prefix: str | None


def _load_json(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load %s: %s", path, e)
    return {}


def _get_provider_pricing() -> dict[str, Any]:
    return _load_json(_PROVIDER_PRICING_PATH)


def _get_customer_pricing() -> dict[str, Any]:
    return _load_json(_CUSTOMER_PRICING_PATH)


def get_fx_rate() -> tuple[float, str]:
    """
    Returns (rate, source). Defaults to USD_BRL_RATE env var or 5.00.
    Does not fetch external exchange rates by default.
    """
    rate = float(os.environ.get("USD_BRL_RATE", "5.00"))
    return rate, "manual_env"


def estimate_provider_cost(
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> ProviderCostResult:
    """
    Estimates the provider's cost for a request in USD and BRL.
    Uses config/provider-pricing.example.json for pricing.
    Returns ProviderCostResult with pricing_configured flag.
    """
    pricing = _get_provider_pricing()
    providers = pricing.get("providers", {})
    prov_cfg = providers.get(provider, {})
    fx_rate, fx_source = get_fx_rate()

    pricing_configured = prov_cfg.get("pricing_configured", False)

    if not pricing_configured:
        return ProviderCostResult(
            provider=provider,
            cost_usd=0.0,
            cost_brl=0.0,
            pricing_configured=False,
            fx_rate=fx_rate,
            fx_rate_source=fx_source,
            details={"pricing_configured": False},
        )

    prompt_rate = float(prov_cfg.get("cost_usd_per_1k_prompt", 0.0))
    completion_rate = float(prov_cfg.get("cost_usd_per_1k_completion", 0.0))

    prompt_cost = (prompt_tokens / 1000.0) * prompt_rate
    completion_cost = (completion_tokens / 1000.0) * completion_rate
    cost_usd = prompt_cost + completion_cost
    cost_brl = cost_usd * fx_rate

    return ProviderCostResult(
        provider=provider,
        cost_usd=round(cost_usd, 8),
        cost_brl=round(cost_brl, 8),
        pricing_configured=True,
        fx_rate=fx_rate,
        fx_rate_source=fx_source,
        details={
            "prompt_rate_per_1k": prompt_rate,
            "completion_rate_per_1k": completion_rate,
            "prompt_cost": round(prompt_cost, 8),
            "completion_cost": round(completion_cost, 8),
        },
    )


def calculate_customer_price(
    plan_code: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    cache_hit: bool = False,
) -> CustomerPriceResult:
    """
    Calculates the price charged to the customer for a request.
    Uses config/customer-pricing.example.json for per-plan pricing.
    Applies cache discount if configured.
    """
    pricing = _get_customer_pricing()
    plans = pricing.get("plans", {})
    plan_cfg = plans.get(plan_code, {})
    default_markup = float(pricing.get("default_markup_percent", 50))
    cache_discount = float(pricing.get("cache_discount_percent", 50))

    price_1k_prompt = float(plan_cfg.get("price_brl_per_1k_prompt", 0.0))
    price_1k_completion = float(plan_cfg.get("price_brl_per_1k_completion", 0.0))
    markup = float(plan_cfg.get("markup_percent", default_markup))

    if price_1k_prompt == 0 and price_1k_completion == 0 and markup > 0:
        prov_cost = estimate_provider_cost("local", prompt_tokens, completion_tokens)
        base_cost = prov_cost.cost_brl
        price_no_discount = base_cost * (1 + markup / 100.0)
    else:
        prompt_price = (prompt_tokens / 1000.0) * price_1k_prompt
        completion_price = (completion_tokens / 1000.0) * price_1k_completion
        price_no_discount = prompt_price + completion_price

    if cache_hit and cache_discount > 0:
        price_brl = price_no_discount * (1 - cache_discount / 100.0)
    else:
        price_brl = price_no_discount

    rule_id = f"plan:{plan_code}" if plan_code else None

    return CustomerPriceResult(
        price_brl=round(price_brl, 8),
        plan_code=plan_code,
        markup_percent=markup,
        pricing_rule_id=rule_id,
        details={
            "price_1k_prompt": price_1k_prompt,
            "price_1k_completion": price_1k_completion,
            "markup_percent": markup,
            "cache_discount_percent": cache_discount if cache_hit else 0,
            "base_price_no_discount": round(price_no_discount, 8),
        },
    )


def calculate_margin(provider_cost_brl: float, customer_price_brl: float) -> MarginResult:
    if provider_cost_brl is None or customer_price_brl is None:
        return MarginResult(
            provider_cost_brl=provider_cost_brl or 0.0,
            customer_price_brl=customer_price_brl or 0.0,
            gross_profit_brl=0.0,
            margin_percent=None,
        )
    gross_profit = customer_price_brl - provider_cost_brl
    if customer_price_brl > 0:
        margin = (gross_profit / customer_price_brl) * 100.0
    else:
        margin = None
    return MarginResult(
        provider_cost_brl=round(provider_cost_brl, 8),
        customer_price_brl=round(customer_price_brl, 8),
        gross_profit_brl=round(gross_profit, 8),
        margin_percent=round(margin, 4) if margin is not None else None,
    )


def convert_usd_to_brl(usd_amount: float, fx_rate: float | None = None) -> tuple[float, float, str]:
    rate, source = get_fx_rate() if fx_rate is None else (fx_rate, "manual_env")
    brl = usd_amount * rate
    return round(brl, 8), rate, source


def calculate_financials(
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_hit: bool = False,
    plan_code: str | None = None,
) -> dict[str, Any]:
    prov_cost = estimate_provider_cost(provider, prompt_tokens, completion_tokens)
    cust_price = calculate_customer_price(plan_code, prompt_tokens, completion_tokens, cache_hit=cache_hit)
    margin = calculate_margin(prov_cost.cost_brl, cust_price.price_brl)

    return {
        "provider": provider,
        "plan_code": plan_code,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cache_hit": cache_hit,
        "provider_cost_usd": prov_cost.cost_usd,
        "provider_cost_brl": prov_cost.cost_brl,
        "pricing_configured": prov_cost.pricing_configured,
        "customer_price_brl": cust_price.price_brl,
        "markup_percent": cust_price.markup_percent,
        "gross_profit_brl": margin.gross_profit_brl,
        "margin_percent": margin.margin_percent,
        "fx_rate": prov_cost.fx_rate,
        "fx_rate_source": prov_cost.fx_rate_source,
        "pricing_rule_id": cust_price.pricing_rule_id,
    }


async def record_request_financials(
    session: AsyncSession,
    *,
    client_id: str | Any,
    endpoint_type: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_hit: bool = False,
    latency_ms: int | None = None,
    plan_code: str | None = None,
    requested_model: str | None = None,
    resolved_model: str | None = None,
    api_key_prefix: str | None = None,
    request_log_id: str | None = None,
    pricing_rule_id: str | None = None,
    token_count_method: str | None = None,
    tokens_estimated: bool = True,
) -> RequestFinancial:
    client_id = str(client_id)
    total_tokens = prompt_tokens + completion_tokens
    prov_cost = estimate_provider_cost(provider, prompt_tokens, completion_tokens)
    cust_price = calculate_customer_price(plan_code, prompt_tokens, completion_tokens, cache_hit=cache_hit)
    margin = calculate_margin(prov_cost.cost_brl, cust_price.price_brl)

    record = RequestFinancial(
        id=uuid4(),
        client_id=client_id,
        request_log_id=request_log_id,
        api_key_prefix=api_key_prefix,
        endpoint_type=endpoint_type,
        provider=provider,
        model=model,
        requested_model=requested_model or model,
        resolved_model=resolved_model or model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        token_count_method=token_count_method,
        tokens_estimated=tokens_estimated,
        cache_hit=cache_hit,
        latency_ms=latency_ms,
        provider_cost_usd=prov_cost.cost_usd,
        provider_cost_brl=prov_cost.cost_brl,
        customer_price_brl=cust_price.price_brl,
        gross_profit_brl=margin.gross_profit_brl,
        margin_percent=margin.margin_percent,
        fx_rate=prov_cost.fx_rate,
        fx_rate_source=prov_cost.fx_rate_source,
        pricing_rule_id=pricing_rule_id or cust_price.pricing_rule_id,
    )
    session.add(record)
    await session.commit()
    return record


def get_provider_pricing_config() -> dict[str, Any]:
    return _get_provider_pricing()


def get_customer_pricing_config() -> dict[str, Any]:
    return _get_customer_pricing()
