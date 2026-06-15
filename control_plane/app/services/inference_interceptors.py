import logging
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class InferenceContext:
    session: AsyncSession
    client_id: str
    plan_code: str
    model: str
    endpoint: str
    prompt_tokens: int
    completion_tokens: int
    is_stream: bool
    correlation_id: str
    request: Request
    commercial_guardrail_context: dict | None = None
    qos_tier: Any | None = None
    routes: list[Any] | None = None
    backend_name: str | None = None
    latency_ms: int | None = None
    status_code: int | None = None


class InferenceInterceptor:
    async def pre_routing(self, context: InferenceContext) -> None:
        pass

    async def post_routing(self, context: InferenceContext) -> None:
        pass

    async def post_request(self, context: InferenceContext) -> None:
        pass

    async def on_error(self, context: InferenceContext, error: Exception) -> None:
        pass


class CommercialAnalyticsInterceptor(InferenceInterceptor):
    async def post_routing(self, context: InferenceContext) -> None:
        from app.schemas.routing import TaskType
        from app.services.billing.pricing_engine import (
            calculate_customer_price,
            estimate_provider_cost,
        )
        from app.services.provider_classification import is_cloud_provider
        from app.services.routing import commercial_analytics

        routes = context.routes or []
        selected_pid = routes[0].inference_backend.provider if routes else None
        est_cost, est_rev = 0.0, 0.0

        if selected_pid:
            est_cost_res = estimate_provider_cost(selected_pid, 100, 500)
            est_rev_res = calculate_customer_price(context.plan_code, 100, 500)
            est_cost = est_cost_res.cost_brl
            est_rev = est_rev_res.price_brl

        cg_context = context.commercial_guardrail_context or {}
        blocked = not routes and bool(cg_context.get("blocked_without_fallback"))

        try:
            await commercial_analytics.record_routing_event(
                context.session,
                client_id=context.client_id,
                correlation_id=context.correlation_id,
                endpoint=context.endpoint,
                model_requested=context.model,
                task_type=TaskType.general,
                policy="commercial_profit",
                selected_provider=selected_pid,
                selected_model=routes[0].inference_backend.name if routes else None,
                selected_is_cloud=is_cloud_provider(selected_pid) if selected_pid else False,
                blocked=blocked,
                block_reason="guardrail_block" if blocked else None,
                estimated_cost_brl=est_cost,
                estimated_revenue_brl=est_rev,
                estimated_margin_brl=est_rev - est_cost,
                estimated_margin_percent=((est_rev - est_cost) / est_rev * 100)
                if est_rev > 0
                else 0,
                ranked_routes=routes,
                guardrail_decisions=cg_context.get("blocked_candidates", []),
                qos_tier=context.qos_tier.name if context.qos_tier else None,
                sla_pass=len(routes) > 0,
                qos_priority=context.qos_tier.priority if context.qos_tier else None,
            )
        except Exception as e:
            logger.warning(f"Commercial analytics pre-routing failed: {e}")

    async def post_request(self, context: InferenceContext) -> None:
        from app.services.billing.pricing_engine import (
            calculate_customer_price,
            estimate_provider_cost,
        )
        from app.services.routing import commercial_analytics

        try:
            act_cost_res = estimate_provider_cost(
                context.backend_name or "unknown", context.prompt_tokens, context.completion_tokens
            )
            act_rev_res = calculate_customer_price(
                context.plan_code, context.prompt_tokens, context.completion_tokens
            )

            await commercial_analytics.update_actual_financials(
                context.session,
                correlation_id=context.correlation_id,
                actual_cost_brl=act_cost_res.cost_brl,
                actual_revenue_brl=act_rev_res.price_brl,
                latency_ms=context.latency_ms or 0,
            )
        except Exception as e:
            logger.warning(f"Commercial analytics post-request failed: {e}")


class InterceptorChain:
    def __init__(self):
        self.interceptors: list[InferenceInterceptor] = []

    def add(self, interceptor: InferenceInterceptor):
        self.interceptors.append(interceptor)

    async def execute_pre_routing(self, context: InferenceContext):
        for i in self.interceptors:
            await i.pre_routing(context)

    async def execute_post_routing(self, context: InferenceContext):
        for i in self.interceptors:
            await i.post_routing(context)

    async def execute_post_request(self, context: InferenceContext):
        for i in self.interceptors:
            await i.post_request(context)

    async def execute_on_error(self, context: InferenceContext, error: Exception):
        for i in reversed(self.interceptors):
            await i.on_error(context, error)


def get_commercial_interceptor_chain() -> InterceptorChain:
    chain = InterceptorChain()
    from app.core.config import get_settings

    if getattr(get_settings(), "commercial_routing_analytics_enabled", True):
        chain.add(CommercialAnalyticsInterceptor())
    return chain
