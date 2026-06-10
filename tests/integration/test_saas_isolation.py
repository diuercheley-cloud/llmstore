from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.models.core.inference_backend import InferenceBackend
from app.models.core.model_backend_route import ModelBackendRoute
from app.models.core.model_registry import ModelRegistry
from app.services.model_policy import plan_routing_order


def mock_route(provider: str, name: str):
    route = MagicMock(spec=ModelBackendRoute)
    route.inference_backend = MagicMock(spec=InferenceBackend)
    route.inference_backend.provider = provider
    route.inference_backend.name = name
    route.inference_backend.is_active = True
    route.state = "healthy"
    route.priority = 1
    route.weight = 100
    route.id = uuid4()
    return route

@pytest.mark.asyncio
async def test_plan_routing_order_respects_guardrail():
    model = MagicMock(spec=ModelRegistry)
    model.backend_routes = [
        mock_route("openai", "gpt-4"),
        mock_route("local", "llama-3"),
    ]
    model.inference_backend = None
    
    # Without guardrail
    with patch("app.services.model_policy.get_routing_candidates", return_value=model.backend_routes):
        routes = plan_routing_order(model, cloud_blocked_by_guardrail=False)
        assert len(routes) == 2
        providers = {r.inference_backend.provider for r in routes}
        assert "openai" in providers
        assert "local" in providers

    # With guardrail
    with patch("app.services.model_policy.get_routing_candidates", return_value=model.backend_routes):
        routes = plan_routing_order(model, cloud_blocked_by_guardrail=True)
        assert len(routes) == 1
        assert routes[0].inference_backend.provider == "local"

@pytest.mark.asyncio
async def test_plan_routing_order_no_local_fallback():
    model = MagicMock(spec=ModelRegistry)
    model.backend_routes = [
        mock_route("openai", "gpt-4"),
        mock_route("anthropic", "claude-3"),
    ]
    model.inference_backend = None
    
    # With guardrail and ONLY cloud routes
    with patch("app.services.model_policy.get_routing_candidates", return_value=model.backend_routes):
        routes = plan_routing_order(model, cloud_blocked_by_guardrail=True)
        assert len(routes) == 0
