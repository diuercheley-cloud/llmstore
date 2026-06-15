from app.contracts.routing import (
    RoutingCapabilities,
    RoutingContract,
    RoutingDecision,
    RoutingInput,
)


class MockRouter(RoutingContract):
    def route(self, input_data: RoutingInput) -> RoutingDecision:
        return RoutingDecision(
            selected_provider="local",
            selected_model="local-model",
            selected_backend="local",
            reason="test",
            policy_applied=input_data.strategy,
        )

    def get_policy(self) -> dict:
        return {"default": "local"}

    def capabilities(self) -> RoutingCapabilities:
        return RoutingCapabilities(cost_aware_routing=True)

    def validate_contract(self) -> bool:
        return True


def test_routing_contract_implementation():
    router = MockRouter()
    assert router.validate_contract() is True

    inp = RoutingInput(requested_model="gpt-4", strategy="lowest_cost")
    decision = router.route(inp)
    assert decision.selected_provider == "local"
    assert decision.policy_applied == "lowest_cost"

    caps = router.capabilities()
    assert caps.cost_aware_routing is True
