import pytest
import uuid
from app.models.operations.adapter_registry import SignedAdapterRegistryEntry
from app.models.operations.adapter_sandbox import AdapterManifest
from app.services.operations.adapter_promotion.gates import AdapterPromotionGateService

def test_evaluate_gates_basic():
    service = AdapterPromotionGateService()
    client_id = uuid.uuid4()
    entry = SignedAdapterRegistryEntry(
        client_id=client_id,
        adapter_name="test",
        adapter_version="1.0.0",
        registry_status="approved",
        signature="sig"
    )
    manifest = AdapterManifest(client_id=client_id, adapter_name="test", adapter_version="1.0.0")
    
    context = {
        "sandbox_simulation_passed": True,
        "no_policy_violations": True,
        "staging_simulation_passed": True,
        "production_approval_granted": True
    }
    
    results = service.evaluate_gates(entry, "production_eligible", manifest, context)
    assert all(r["gate_status"] == "passed" for r in results)

def test_evaluate_gates_failure():
    service = AdapterPromotionGateService()
    client_id = uuid.uuid4()
    entry = SignedAdapterRegistryEntry(
        client_id=client_id,
        adapter_name="test",
        adapter_version="1.0.0",
        registry_status="revoked", # Failure
        signature="sig"
    )
    manifest = AdapterManifest(client_id=client_id, adapter_name="test", adapter_version="1.0.0")
    
    context = {
        "sandbox_simulation_passed": True,
        "no_policy_violations": True
    }
    
    results = service.evaluate_gates(entry, "staging_simulated", manifest, context)
    
    # not_revoked should fail
    not_revoked_gate = next(r for r in results if r["gate_name"] == "not_revoked")
    assert not_revoked_gate["gate_status"] == "failed"
    
    explanation = service.explain_gate_results(results)
    assert "not_revoked" in explanation
