import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Default pricing table (USD per 1M tokens)
DEFAULT_PRICING: dict[str, dict[str, Any]] = {
    "gpt-4o": {
        "prompt_token_price_per_1m": 5.0,
        "completion_token_price_per_1m": 15.0,
        "currency": "USD"
    },
    "gpt-4o-mini": {
        "prompt_token_price_per_1m": 0.15,
        "completion_token_price_per_1m": 0.6,
        "currency": "USD"
    },
    "claude-3-5-sonnet-20241022": {
        "prompt_token_price_per_1m": 3.0,
        "completion_token_price_per_1m": 15.0,
        "currency": "USD"
    },
    "claude-3-5-haiku-20241022": {
        "prompt_token_price_per_1m": 0.25,
        "completion_token_price_per_1m": 1.25,
        "currency": "USD"
    },
    "claude-sonnet-4-20250514": {
        "prompt_token_price_per_1m": 3.0,
        "completion_token_price_per_1m": 15.0,
        "currency": "USD"
    },
    "gemini-2.5-flash": {
        "prompt_token_price_per_1m": 0.10,
        "completion_token_price_per_1m": 0.40,
        "currency": "USD"
    },
    "gemini-2.5-pro": {
        "prompt_token_price_per_1m": 1.25,
        "completion_token_price_per_1m": 5.0,
        "currency": "USD"
    },
    "o3-mini": {
        "prompt_token_price_per_1m": 1.10,
        "completion_token_price_per_1m": 4.40,
        "currency": "USD"
    },
    "deepseek-chat": {
        "prompt_token_price_per_1m": 0.27,
        "completion_token_price_per_1m": 1.10,
        "currency": "USD"
    },
}


@dataclass
class PricingResult:
    cost: float
    currency: str
    model_key: str
    known: bool


class PricingManager:
    def __init__(self, pricing_file: str | None = None):
        self.pricing: dict[str, dict[str, Any]] = DEFAULT_PRICING.copy()
        self._model_override: str | None = None
        if pricing_file:
            self.load_pricing(pricing_file)

    def set_model_override(self, model: str | None) -> None:
        self._model_override = model

    def load_pricing(self, pricing_file: str):
        try:
            with open(pricing_file) as f:
                custom_pricing = json.load(f)
                self.pricing.update(custom_pricing)
                logger.info(f"Loaded custom pricing from {pricing_file}")
        except Exception as e:
            logger.error(f"Failed to load pricing file {pricing_file}: {e}")

    def _lookup(self, model: str) -> tuple[dict[str, Any] | None, str]:
        exact = self.pricing.get(model)
        if exact is not None:
            return exact, model
        for prefix in sorted(self.pricing.keys(), key=len, reverse=True):
            if model.startswith(prefix):
                return self.pricing[prefix], prefix
        return None, model

    def calculate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int,
        reasoning_tokens: int | None = None,
    ) -> PricingResult | None:
        lookup_model = self._model_override or model
        model_pricing, matched_key = self._lookup(lookup_model)

        if model_pricing is None:
            logger.debug(
                "Unknown model '%s' (looked up as '%s'); no pricing data available",
                model, lookup_model,
            )
            return None

        p_price: float = float(model_pricing.get("prompt_token_price_per_1m", 0.0))
        c_price: float = float(model_pricing.get("completion_token_price_per_1m", 0.0))
        currency: str = str(model_pricing.get("currency", "USD"))

        prompt_cost = (prompt_tokens / 1_000_000) * p_price
        completion_cost = (completion_tokens / 1_000_000) * c_price

        if reasoning_tokens is not None:
            effective_completion = completion_tokens - reasoning_tokens
            if effective_completion < 0:
                effective_completion = 0
            prompt_cost = ((prompt_tokens + reasoning_tokens) / 1_000_000) * p_price
            completion_cost = (effective_completion / 1_000_000) * c_price

        return PricingResult(
            cost=round(prompt_cost + completion_cost, 6),
            currency=currency,
            model_key=matched_key,
            known=True,
        )

    def get_currency(self, model: str) -> str:
        lookup_model = self._model_override or model
        model_pricing, _ = self._lookup(lookup_model)
        if model_pricing is None:
            return "USD"
        return str(model_pricing.get("currency", "USD"))
