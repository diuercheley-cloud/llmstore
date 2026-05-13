from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.routing import (
    EndpointType,
    RoutingDecision,
    RoutingStrategy,
    SmartRouterInput,
)

logger = logging.getLogger(__name__)

_router_instance: SmartRouter | None = None


def _load_policy() -> dict[str, Any]:
    policy_path = Path(__file__).resolve().parents[4] / "config" / "routing-policies.example.json"
    defaults = {
        "default_strategy": "local_first",
        "allow_cloud_fallback": False,
        "complexity_threshold": 4000,
        "coding_provider_preference": "anthropic",
        "low_budget_provider_preference": "deepseek",
        "premium_provider_preference": "openai",
        "max_provider_cost_per_request_brl": 0.50,
        "tenant_policy_overrides": {},
        "fallback_order": ["local", "lmstudio", "mock"],
    }
    if policy_path.exists():
        try:
            with open(policy_path) as f:
                loaded = json.load(f)
            defaults.update(loaded)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load routing policy file: %s", e)
    return defaults


FALLBACK_ORDER: list[str] = ["local", "lmstudio", "mock"]
CLOUD_PROVIDERS = {"openai", "anthropic", "deepseek", "openrouter"}
LOCAL_PROVIDERS = {"local", "lmstudio", "mock"}
EMBEDDINGS_PROVIDERS = {"local", "openai"}
RAG_CAPABLE_PROVIDERS = {"local", "openai", "anthropic"}
LOW_COST_ORDER = ["deepseek", "local", "lmstudio", "openai", "anthropic", "mock"]
PREMIUM_ORDER = ["openai", "anthropic", "local", "lmstudio", "mock"]
CODING_PROVIDER_PREFERENCE = "anthropic"
LOW_BUDGET_PROVIDER_PREFERENCE = "deepseek"
PREMIUM_PROVIDER_PREFERENCE = "openai"

_last_decisions: list[dict[str, Any]] = []


def _sanitize_reason(reason: str) -> str:
    sanitized = reason.replace("\n", " ").replace("\r", " ")
    sensitive_keywords = ["api_key", "api-key", "apikey", "secret", "token", "password", "authorization"]
    for kw in sensitive_keywords:
        sanitized = sanitized.replace(kw, "***")
    return sanitized[:500]


def _get_provider_config(provider_id: str) -> dict[str, Any]:
    settings = get_settings()
    config_map = {
        "local": {"enabled": True, "configured": True},
        "lmstudio": {
            "enabled": settings.lmstudio_enabled,
            "configured": bool(settings.lmstudio_base_url),
        },
        "openai": {
            "enabled": "openai" in settings.providers_enabled,
            "configured": bool(settings.openai_api_key),
        },
        "anthropic": {
            "enabled": "anthropic" in settings.providers_enabled,
            "configured": bool(settings.anthropic_api_key),
        },
        "deepseek": {
            "enabled": "deepseek" in settings.providers_enabled,
            "configured": bool(settings.deepseek_api_key),
        },
        "openrouter": {
            "enabled": "openrouter" in settings.providers_enabled,
            "configured": bool(settings.openrouter_api_key),
        },
        "mock": {"enabled": True, "configured": True},
    }
    return config_map.get(provider_id, {"enabled": False, "configured": False})


def _is_provider_available(provider_id: str) -> bool:
    cfg = _get_provider_config(provider_id)
    if not (cfg.get("enabled", False) and cfg.get("configured", False)):
        return False
    if provider_id in LOCAL_PROVIDERS:
        force_fail = get_settings().routing_test_force_local_failure
        if force_fail:
            return False
    return True


def _get_cloud_providers_enabled() -> bool:
    return get_settings().cloud_providers_enabled


def _estimate_cost(provider_id: str, prompt_tokens: int, max_output_tokens: int) -> float:
    rates: dict[str, dict[str, float]] = {
        "local": {"prompt": 0.0, "completion": 0.0},
        "lmstudio": {"prompt": 0.0, "completion": 0.0},
        "mock": {"prompt": 0.0, "completion": 0.0},
        "openai": {"prompt": 0.0000025, "completion": 0.00001},
        "anthropic": {"prompt": 0.000003, "completion": 0.000015},
        "deepseek": {"prompt": 0.0000005, "completion": 0.000002},
        "openrouter": {"prompt": 0.000002, "completion": 0.000008},
    }
    r = rates.get(provider_id, {"prompt": 0.0, "completion": 0.0})
    return (prompt_tokens * r["prompt"]) + (max_output_tokens * r["completion"])


def _provider_health(provider_id: str) -> str:
    try:
        from app.services.providers.registry import get_provider
        prov = get_provider(provider_id)
        if prov is None:
            return "unregistered"
        if not prov.enabled:
            return "disabled"
        if not prov.configured:
            return "unconfigured"
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return "unknown_async"
        except RuntimeError:
            pass
        return "healthy"
    except Exception:
        return "error"


class SmartRouter:
    def __init__(self) -> None:
        self.policy = _load_policy()
        self.decision_log: list[dict[str, Any]] = []

    @property
    def default_strategy(self) -> str:
        return self.policy.get("default_strategy", "local_first")

    def route(self, inp: SmartRouterInput) -> RoutingDecision:
        warnings: list[str] = []
        strategies_considered: list[str] = [
            inp.strategy.value if isinstance(inp.strategy, RoutingStrategy) else str(inp.strategy)
        ]
        provider_states: dict[str, str] = {}
        fallback_chain: list[str] = []

        strategy = inp.strategy
        if isinstance(strategy, str):
            try:
                strategy = RoutingStrategy(strategy)
            except ValueError:
                strategy = RoutingStrategy.local_first

        cloud_allowed = inp.cloud_allowed and _get_cloud_providers_enabled()
        cloud_enabled = _get_cloud_providers_enabled()

        if inp.cloud_allowed and not cloud_enabled:
            warnings.append("cloud_allowed=true but cloud providers globally disabled")

        strat_val = (
            inp.strategy.value if isinstance(inp.strategy, RoutingStrategy)
            else str(inp.strategy) if inp.strategy else "local_first"
        )

        for pid in ["local", "lmstudio", "openai", "anthropic", "deepseek", "openrouter", "mock"]:
            provider_states[pid] = _provider_health(pid)

        result = self._apply_strategy(inp, strategy, cloud_allowed, cloud_enabled, provider_states, warnings)

        selected_provider = result["selected_provider"]
        selected_model = result["selected_model"]
        selected_backend = result.get("selected_backend")
        reason = result.get("reason", "strategy applied")
        fallback_chain = result.get("fallback_chain", fallback_chain)
        cloud_used = selected_provider in CLOUD_PROVIDERS

        if cloud_used and inp.cloud_allowed is False:
            warnings.append("cloud provider selected despite cloud_allowed=false; check policy override")

        cost = _estimate_cost(selected_provider, inp.prompt_estimated_tokens, inp.max_output_tokens)
        if cost > self.policy.get("max_provider_cost_per_request_brl", 0.50) and cloud_used:
            warnings.append(f"estimated cost ${cost:.6f} exceeds configured max")
            if not cloud_allowed:
                selected_provider = "local"
                selected_model = selected_model or "local-model"
                selected_backend = "local"
                cloud_used = False
                reason = "cost exceeded; fell back to local"
                fallback_chain.append("local")

        if inp.wallet_balance_brl is not None and inp.wallet_balance_brl <= 0 and cloud_allowed:
            warnings.append("wallet balance depleted; blocking cloud routing")
            if selected_provider in CLOUD_PROVIDERS:
                selected_provider = "local"
                selected_model = "local-model"
                cloud_used = False
                reason = "insufficient balance; fell back to local"
                fallback_chain.append("local")

        decision = RoutingDecision(
            selected_provider=selected_provider,
            selected_model=selected_model or "local-model",
            selected_backend=selected_backend or selected_provider,
            reason=_sanitize_reason(reason),
            fallback_chain=fallback_chain,
            estimated_cost_brl=cost,
            policy_applied=strat_val,
            cloud_used=cloud_used,
            warnings=warnings,
        )
        self._log_decision(inp, decision, strategies_considered, provider_states)
        return decision

    def _apply_strategy(
        self,
        inp: SmartRouterInput,
        strategy: RoutingStrategy,
        cloud_allowed: bool,
        cloud_enabled: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        if strategy == RoutingStrategy.local_first:
            return self._strategy_local_first(inp, cloud_allowed, provider_states, warnings)
        elif strategy == RoutingStrategy.lowest_cost:
            return self._strategy_lowest_cost(inp, cloud_allowed, cloud_enabled, provider_states, warnings)
        elif strategy == RoutingStrategy.premium_quality:
            return self._strategy_premium(inp, cloud_allowed, cloud_enabled, provider_states, warnings)
        elif strategy == RoutingStrategy.coding:
            return self._strategy_coding(inp, cloud_allowed, cloud_enabled, provider_states, warnings)
        elif strategy == RoutingStrategy.embeddings_optimized:
            return self._strategy_embeddings(inp, cloud_allowed, cloud_enabled, provider_states, warnings)
        elif strategy == RoutingStrategy.rag_optimized:
            return self._strategy_rag(inp, cloud_allowed, cloud_enabled, provider_states, warnings)
        elif strategy == RoutingStrategy.fallback_only:
            return self._strategy_fallback(inp, provider_states, warnings)
        return self._strategy_local_first(inp, cloud_allowed, provider_states, warnings)

    def _strategy_local_first(
        self,
        inp: SmartRouterInput,
        cloud_allowed: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        for pid in self.policy.get("fallback_order", FALLBACK_ORDER):
            if not cloud_allowed and pid in CLOUD_PROVIDERS:
                continue
            if provider_states.get(pid) in ("healthy", "unknown_async"):
                if _is_provider_available(pid):
                    fallback_chain.append(pid)
                    return {
                        "selected_provider": pid,
                        "selected_model": f"{pid}-model",
                        "selected_backend": pid,
                        "reason": f"local_first strategy: selected {pid}",
                        "fallback_chain": fallback_chain,
                    }
            else:
                fallback_chain.append(pid)
                warnings.append(f"provider {pid} state={provider_states.get(pid)}; skipped")

        fallback_chain.append("mock")
        return {
            "selected_provider": "mock",
            "selected_model": "mock-model",
            "selected_backend": "mock",
            "reason": "all providers unavailable; using mock fallback",
            "fallback_chain": fallback_chain,
        }

    def _strategy_lowest_cost(
        self,
        inp: SmartRouterInput,
        cloud_allowed: bool,
        cloud_enabled: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        for pid in LOW_COST_ORDER:
            if not cloud_allowed and pid in CLOUD_PROVIDERS:
                continue
            if provider_states.get(pid) in ("healthy", "unknown_async"):
                if _is_provider_available(pid):
                    fallback_chain.append(pid)
                    return {
                        "selected_provider": pid,
                        "selected_model": f"{pid}-model",
                        "selected_backend": pid,
                        "reason": f"lowest_cost strategy: selected {pid}",
                        "fallback_chain": fallback_chain,
                    }
            else:
                warnings.append(f"provider {pid} state={provider_states.get(pid)}; skipped")
                fallback_chain.append(pid)
        return self._strategy_local_first(inp, cloud_allowed, provider_states, warnings)

    def _strategy_premium(
        self,
        inp: SmartRouterInput,
        cloud_allowed: bool,
        cloud_enabled: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        preferred = self.policy.get("premium_provider_preference", PREMIUM_PROVIDER_PREFERENCE)
        if cloud_allowed and cloud_enabled:
            if provider_states.get(preferred) in ("healthy", "unknown_async") and _is_provider_available(preferred):
                fallback_chain.append(preferred)
                return {
                    "selected_provider": preferred,
                    "selected_model": f"{preferred}-model",
                    "selected_backend": preferred,
                    "reason": f"premium_quality strategy: selected preferred {preferred}",
                    "fallback_chain": fallback_chain,
                }
            warnings.append(f"preferred provider {preferred} unavailable")
            for pid in PREMIUM_ORDER:
                if pid == preferred:
                    continue
                if not cloud_allowed and pid in CLOUD_PROVIDERS:
                    continue
                if provider_states.get(pid) in ("healthy", "unknown_async") and _is_provider_available(pid):
                    fallback_chain.append(pid)
                    return {
                        "selected_provider": pid,
                        "selected_model": f"{pid}-model",
                        "selected_backend": pid,
                        "reason": f"premium_quality strategy: fell back to {pid}",
                        "fallback_chain": fallback_chain,
                    }
                warnings.append(f"provider {pid} unavailable; skipped")
                fallback_chain.append(pid)
        return self._strategy_local_first(inp, cloud_allowed, provider_states, warnings)

    def _strategy_coding(
        self,
        inp: SmartRouterInput,
        cloud_allowed: bool,
        cloud_enabled: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        preferred = self.policy.get("coding_provider_preference", CODING_PROVIDER_PREFERENCE)
        if cloud_allowed and cloud_enabled:
            if provider_states.get(preferred) in ("healthy", "unknown_async") and _is_provider_available(preferred):
                fallback_chain.append(preferred)
                return {
                    "selected_provider": preferred,
                    "selected_model": f"{preferred}-model",
                    "selected_backend": preferred,
                    "reason": f"coding strategy: selected {preferred}",
                    "fallback_chain": fallback_chain,
                }
            warnings.append(f"coding provider {preferred} unavailable")
            fallback_chain.append(preferred)
        return self._strategy_local_first(inp, cloud_allowed, provider_states, warnings)

    def _strategy_embeddings(
        self,
        inp: SmartRouterInput,
        cloud_allowed: bool,
        cloud_enabled: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        for pid in ["local", "openai", "lmstudio", "mock"]:
            if not cloud_allowed and pid in CLOUD_PROVIDERS:
                continue
            if provider_states.get(pid) in ("healthy", "unknown_async") and _is_provider_available(pid):
                fallback_chain.append(pid)
                return {
                    "selected_provider": pid,
                    "selected_model": f"{pid}-embedding-model",
                    "selected_backend": pid,
                    "reason": f"embeddings_optimized strategy: selected {pid}",
                    "fallback_chain": fallback_chain,
                }
            warnings.append(f"provider {pid} unavailable; skipped")
            fallback_chain.append(pid)
        return {
            "selected_provider": "mock",
            "selected_model": "mock-embedding-model",
            "selected_backend": "mock",
            "reason": "embeddings_optimized: all providers unavailable; using mock",
            "fallback_chain": fallback_chain,
        }

    def _strategy_rag(
        self,
        inp: SmartRouterInput,
        cloud_allowed: bool,
        cloud_enabled: bool,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        for pid in ["local", "openai", "anthropic", "lmstudio", "mock"]:
            if not cloud_allowed and pid in CLOUD_PROVIDERS:
                continue
            if provider_states.get(pid) in ("healthy", "unknown_async") and _is_provider_available(pid):
                fallback_chain.append(pid)
                return {
                    "selected_provider": pid,
                    "selected_model": f"{pid}-model",
                    "selected_backend": pid,
                    "reason": f"rag_optimized strategy: selected {pid}",
                    "fallback_chain": fallback_chain,
                }
            warnings.append(f"provider {pid} unavailable; skipped")
            fallback_chain.append(pid)
        return {
            "selected_provider": "mock",
            "selected_model": "mock-model",
            "selected_backend": "mock",
            "reason": "rag_optimized: all providers unavailable; using mock",
            "fallback_chain": fallback_chain,
        }

    def _strategy_fallback(
        self,
        inp: SmartRouterInput,
        provider_states: dict[str, str],
        warnings: list[str],
    ) -> dict[str, Any]:
        fallback_chain: list[str] = []
        for pid in self.policy.get("fallback_order", FALLBACK_ORDER):
            if provider_states.get(pid) in ("healthy", "unknown_async"):
                if _is_provider_available(pid):
                    fallback_chain.append(pid)
                    return {
                        "selected_provider": pid,
                        "selected_model": f"{pid}-model",
                        "selected_backend": pid,
                        "reason": f"fallback_only strategy: selected {pid}",
                        "fallback_chain": fallback_chain,
                    }
            warnings.append(f"provider {pid} in state {provider_states.get(pid)}; skipped")
            fallback_chain.append(pid)
        return {
            "selected_provider": "mock",
            "selected_model": "mock-model",
            "selected_backend": "mock",
            "reason": "fallback_only: all providers exhausted; using mock",
            "fallback_chain": fallback_chain,
        }

    def _log_decision(
        self,
        inp: SmartRouterInput,
        decision: RoutingDecision,
        strategies_considered: list[str],
        provider_states: dict[str, str],
    ) -> None:
        entry: dict[str, Any] = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requested_model": inp.requested_model or "unspecified",
            "resolved_model": decision.selected_model,
            "selected_provider": decision.selected_provider,
            "routing_strategy": decision.policy_applied or "unknown",
            "fallback_used": len(decision.fallback_chain) > 1,
            "fallback_reason": decision.reason if len(decision.fallback_chain) > 1 else None,
            "cloud_used": decision.cloud_used,
            "estimated_cost_brl": decision.estimated_cost_brl,
            "sanitized_reason": _sanitize_reason(decision.reason),
            "endpoint_type": inp.endpoint_type.value if isinstance(inp.endpoint_type, EndpointType) else str(inp.endpoint_type),
            "strategies_considered": strategies_considered,
            "provider_states": dict(provider_states),
        }
        self.decision_log.append(entry)
        _last_decisions.append(entry)
        if len(_last_decisions) > 1000:
            _last_decisions.pop(0)
        logger.debug("Routing decision: provider=%s model=%s strategy=%s", decision.selected_provider, decision.selected_model, decision.policy_applied)

    def simulate(self, inp: SmartRouterInput) -> tuple[RoutingDecision, list[str], dict[str, str], dict[str, object]]:
        strategies_to_try = [
            RoutingStrategy.local_first,
            RoutingStrategy.lowest_cost,
            RoutingStrategy.premium_quality,
            RoutingStrategy.coding,
            RoutingStrategy.embeddings_optimized,
            RoutingStrategy.rag_optimized,
            RoutingStrategy.fallback_only,
        ]
        if inp.strategy and inp.strategy in strategies_to_try:
            strategies_to_try = [inp.strategy] + [s for s in strategies_to_try if s != inp.strategy]

        all_results: list[tuple[str, RoutingDecision]] = []
        for strat in strategies_to_try:
            sim_inp = inp.model_copy(update={"strategy": strat})
            decision = self.route(sim_inp)
            all_results.append((strat.value, decision))

        config_snapshot: dict[str, object] = {
            "default_strategy": self.policy.get("default_strategy"),
            "allow_cloud_fallback": self.policy.get("allow_cloud_fallback"),
            "cloud_providers_enabled": _get_cloud_providers_enabled(),
            "fallback_order": self.policy.get("fallback_order"),
        }

        primary_strategy = inp.strategy if isinstance(inp.strategy, RoutingStrategy) else RoutingStrategy.local_first
        primary_decision = next((d for s, d in all_results if s == primary_strategy.value), all_results[0][1])
        strategies_considered = [s for s, _ in all_results]
        provider_states = {pid: _provider_health(pid) for pid in ["local", "lmstudio", "openai", "anthropic", "deepseek", "openrouter", "mock"]}

        return primary_decision, strategies_considered, provider_states, config_snapshot

    def get_last_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(_last_decisions[-limit:])

    def get_policy(self) -> dict[str, Any]:
        return dict(self.policy)

    def reset(self) -> None:
        self.decision_log.clear()
        _last_decisions.clear()


def get_smart_router() -> SmartRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartRouter()
    return _router_instance


def reset_smart_router() -> None:
    global _router_instance
    _router_instance = None
