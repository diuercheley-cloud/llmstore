from typing import Any, Protocol, runtime_checkable

from app.contracts.base import BaseContract, ContractCapability
from pydantic import BaseModel, Field


class RoutingInput(BaseModel):
    requested_model: str | None = None
    strategy: str = "local_first"
    prompt_estimated_tokens: int = 0
    max_output_tokens: int = 0
    cloud_allowed: bool = True
    wallet_balance_brl: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    selected_provider: str
    selected_model: str
    selected_backend: str
    reason: str
    fallback_chain: list[str] = Field(default_factory=list)
    estimated_cost_brl: float = 0.0
    policy_applied: str
    cloud_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class RoutingCapabilities(ContractCapability):
    dynamic_strategies: bool = False
    cost_aware_routing: bool = False
    multi_region: bool = False


@runtime_checkable
class RoutingContract(BaseContract, Protocol):
    """
    Contract for Smart Routers.
    """

    def route(self, input_data: RoutingInput) -> RoutingDecision:
        """Determines the best provider/model for a given request."""
        ...

    def get_policy(self) -> dict[str, Any]:
        """Returns the current routing policy."""
        ...

    def capabilities(self) -> RoutingCapabilities:
        """Returns capabilities supported by the router."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["route", "get_policy", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
