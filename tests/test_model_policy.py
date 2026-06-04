import json
import random

import pytest
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.model_policy import (
    get_effective_allowed_models,
    get_effective_allowed_models_for_session,
    plan_routing_order,
    resolve_requested_model,
    serialize_model_card,
)
from fastapi import HTTPException


def test_get_effective_allowed_models_prefers_client_override():
    client = Client(
        name="demo",
        allowed_models_json=json.dumps(["client-model", "alias-a"]),
    )
    client.billing_plan = BillingPlan(
        code="basic",
        name="Basic",
        rate_limit_per_minute=10,
        daily_token_quota=50000,
        monthly_token_quota=500000,
        max_output_tokens=512,
        allow_streaming=True,
        is_active=True,
        allowed_models_json=json.dumps(["plan-model"]),
    )

    assert get_effective_allowed_models(client) == {"client-model", "alias-a"}


def test_get_effective_allowed_models_falls_back_to_plan():
    client = Client(name="demo")
    client.billing_plan = BillingPlan(
        code="basic",
        name="Basic",
        rate_limit_per_minute=10,
        daily_token_quota=50000,
        monthly_token_quota=500000,
        max_output_tokens=512,
        allow_streaming=True,
        is_active=True,
        allowed_models_json=json.dumps(["gemma", "phi"]),
    )

    assert get_effective_allowed_models(client) == {"gemma", "phi"}


@pytest.mark.asyncio
async def test_get_effective_allowed_models_for_session_reloads_billing_plan(monkeypatch):
    client = Client(name="demo")

    class DummyPlan:
        allowed_models_json = json.dumps(["safe-model"])

    class DummyLoadedClient:
        id = client.id
        billing_plan = DummyPlan()
        allowed_models_json = None

    class DummyResult:
        def scalar_one_or_none(self):
            return DummyLoadedClient()

    class DummySession:
        async def execute(self, _stmt):
            return DummyResult()

    allowed = await get_effective_allowed_models_for_session(DummySession(), client)
    assert allowed == {"safe-model"}


def test_serialize_model_card_uses_alias_as_public_id():
    model = ModelRegistry(
        model_id="unsloth/gemma-4-E4B-it-GGUF",
        model_alias="gemma",
        provider="llama.cpp",
        model_file="gemma.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
        status="configured",
        metadata_json=json.dumps({"recommended_quantization": "Q4_0"}),
    )
    model.backend_routes = []

    payload = serialize_model_card(model)

    assert payload["id"] == "gemma"
    assert payload["metadata"]["model_id"] == "unsloth/gemma-4-E4B-it-GGUF"
    assert payload["metadata"]["is_default"] is True


def test_plan_routing_order_prefers_healthy_before_degraded():
    model = ModelRegistry(model_id="gemma", provider="llama.cpp", model_file="gemma.gguf", context_length=2048, is_active=True, is_default=True, status="configured")
    healthy_backend = InferenceBackend(name="primary", provider="llama.cpp", backend_url="http://primary", is_active=True, status="healthy")
    degraded_backend = InferenceBackend(name="secondary", provider="llama.cpp", backend_url="http://secondary", is_active=True, status="healthy")
    model.backend_routes = [
        ModelBackendRoute(priority=5, weight=10, state="degraded", inference_backend=degraded_backend),
        ModelBackendRoute(priority=10, weight=10, state="healthy", inference_backend=healthy_backend),
    ]

    ordered = plan_routing_order(model, random.Random(0))

    assert [item.inference_backend.name for item in ordered] == ["primary", "secondary"]


def test_plan_routing_order_uses_weight_inside_same_priority_group():
    model = ModelRegistry(model_id="gemma", provider="llama.cpp", model_file="gemma.gguf", context_length=2048, is_active=True, is_default=True, status="configured")
    high_weight_backend = InferenceBackend(name="high-weight", provider="llama.cpp", backend_url="http://one", is_active=True, status="healthy")
    low_weight_backend = InferenceBackend(name="low-weight", provider="llama.cpp", backend_url="http://two", is_active=True, status="healthy")
    model.backend_routes = [
        ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=high_weight_backend),
        ModelBackendRoute(priority=1, weight=1, state="healthy", inference_backend=low_weight_backend),
    ]

    first_choices = {"high-weight": 0, "low-weight": 0}
    for seed in range(50):
        ordered = plan_routing_order(model, random.Random(seed))
        first_choices[ordered[0].inference_backend.name] += 1

    assert first_choices["high-weight"] > first_choices["low-weight"]


@pytest.mark.asyncio
async def test_resolve_requested_model_rejects_unknown_model(monkeypatch):
    model = ModelRegistry(
        model_id="gemma",
        model_alias="gemma",
        provider="llama.cpp",
        model_file="gemma.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
        status="configured",
    )
    backend = InferenceBackend(name="primary", provider="llama.cpp", backend_url="http://primary", is_active=True, status="healthy")
    model.backend_routes = [ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=backend)]

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)

    with pytest.raises(HTTPException) as exc:
        await resolve_requested_model(None, client=Client(name="demo"), requested_model="model-not-allowed")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_requested_model_allows_explicit_default(monkeypatch):
    model = ModelRegistry(
        model_id="gemma",
        model_alias="gemma",
        provider="llama.cpp",
        model_file="gemma.gguf",
        context_length=2048,
        is_active=True,
        is_default=True,
        status="configured",
    )
    backend = InferenceBackend(name="primary", provider="llama.cpp", backend_url="http://primary", is_active=True, status="healthy")
    model.backend_routes = [ModelBackendRoute(priority=1, weight=100, state="healthy", inference_backend=backend)]

    async def fake_models(_session):
        return [model]

    monkeypatch.setattr("app.services.model_policy.list_active_registry_models", fake_models)
    async def fake_trust(*_args, **_kwargs):
        return {"allowed": True, "trust_state": "disabled", "mode": "disabled"}
    monkeypatch.setattr("app.services.model_policy.enforce_model_trust_or_warn", fake_trust)

    selected, requested = await resolve_requested_model(None, client=Client(name="demo"), requested_model="default")

    assert selected is model
    assert requested == "default"
