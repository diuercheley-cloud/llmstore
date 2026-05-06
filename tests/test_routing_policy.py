import pytest
import json
import uuid
from app.models.client import Client
from app.models.billing_plan import BillingPlan
from app.models.inference_backend import InferenceBackend
from app.models.model_backend_route import ModelBackendRoute
from app.models.model_registry import ModelRegistry
from app.services.model_policy import apply_routing_policy, plan_routing_order


def test_apply_routing_policy_prioritize_backend_type():
    model = ModelRegistry(model_id="test-model")
    vllm_backend = InferenceBackend(name="vllm-primary", provider="vllm", is_active=True)
    llama_backend = InferenceBackend(name="llama-secondary", provider="llama.cpp", is_active=True)
    
    routes = [
        ModelBackendRoute(id=uuid.uuid4(), priority=100, weight=100, state="healthy", inference_backend=llama_backend),
        ModelBackendRoute(id=uuid.uuid4(), priority=100, weight=100, state="healthy", inference_backend=vllm_backend),
    ]
    
    plan = BillingPlan(
        code="premium",
        routing_policy_json=json.dumps({
            "rules": [
                {"action": "prioritize_backend_type", "value": "vllm", "priority_boost": 50}
            ]
        })
    )
    client = Client(name="premium-client", billing_plan=plan)
    
    final = apply_routing_policy(model, client, routes)
    
    assert len(final) == 2
    assert final[0].inference_backend.provider == "vllm"
    assert final[0].priority == 50  # 100 - 50


def test_apply_routing_policy_exclude_backend():
    model = ModelRegistry(model_id="test-model")
    slow_backend = InferenceBackend(name="slow-backend", provider="llama.cpp", is_active=True)
    fast_backend = InferenceBackend(name="fast-backend", provider="llama.cpp", is_active=True)
    
    routes = [
        ModelBackendRoute(id=uuid.uuid4(), priority=100, weight=100, state="healthy", inference_backend=slow_backend),
        ModelBackendRoute(id=uuid.uuid4(), priority=100, weight=100, state="healthy", inference_backend=fast_backend),
    ]
    
    plan = BillingPlan(
        code="free",
        routing_policy_json=json.dumps({
            "rules": [
                {"action": "exclude_backend", "value": "slow-backend"}
            ]
        })
    )
    client = Client(name="free-client", billing_plan=plan)
    
    final = apply_routing_policy(model, client, routes)
    
    assert len(final) == 1
    assert final[0].inference_backend.name == "fast-backend"


def test_plan_routing_order_with_client_policy():
    model = ModelRegistry(
        model_id="test-model", 
        provider="llama.cpp", 
        model_file="test.gguf", 
        context_length=2048,
        is_active=True
    )
    vllm_backend = InferenceBackend(name="vllm-primary", provider="vllm", is_active=True)
    llama_backend = InferenceBackend(name="llama-secondary", provider="llama.cpp", is_active=True)
    
    model.backend_routes = [
        ModelBackendRoute(id=uuid.uuid4(), priority=100, weight=100, state="healthy", inference_backend=llama_backend),
        ModelBackendRoute(id=uuid.uuid4(), priority=100, weight=100, state="healthy", inference_backend=vllm_backend),
    ]
    
    plan = BillingPlan(
        code="premium",
        routing_policy_json=json.dumps({
            "rules": [
                {"action": "prioritize_backend_type", "value": "vllm", "priority_boost": 50}
            ]
        })
    )
    client = Client(name="premium-client", billing_plan=plan)
    
    # plan_routing_order should now accept client
    ordered = plan_routing_order(model, client=client)
    
    assert len(ordered) == 2
    assert ordered[0].inference_backend.provider == "vllm"
