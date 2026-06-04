import pytest
from app.services.governance.policy_engine import PolicyEngineService
from app.services.governance.policy_registry import PolicyRegistryService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_validate_policy_bundle(session: AsyncSession):
    service = PolicyEngineService()
    
    # Valid bundle
    valid, errors = await service.validate_policy_bundle({
        "routing": {"max_cost_per_request_brl": 0.5},
        "billing": {},
        "qos": {}
    })
    assert valid is True
    assert len(errors) == 0
    
    # Invalid bundle
    valid, errors = await service.validate_policy_bundle({
        "routing": {"max_cost_per_request_brl": "expensive"}
    })
    assert valid is False
    assert "routing.max_cost_per_request_brl must be a number" in errors

@pytest.mark.asyncio
async def test_sign_and_validate_policy(session: AsyncSession):
    engine = PolicyEngineService()
    registry = PolicyRegistryService()
    
    rules = {"routing": {"force_local_only": True}}
    bundle = await registry.create_policy_bundle(session, "Sign Test", "1.0", "routing", rules)
    
    signature = engine.sign_policy_bundle(rules, bundle.immutable_hash)
    bundle.signature = signature
    
    assert engine.validate_policy_signature(bundle) is True
    
    # Tamper with rules
    bundle.rules_json = {"routing": {"force_local_only": False}}
    assert engine.validate_policy_signature(bundle) is False

@pytest.mark.asyncio
async def test_simulate_policy_bundle(session: AsyncSession):
    engine = PolicyEngineService()
    registry = PolicyRegistryService()
    
    bundle = await registry.create_policy_bundle(session, "Sim Test", "1.0", "routing", {"r": 1})
    
    results = await engine.simulate_policy_bundle(session, bundle.id, {"user_id": "test"})
    
    assert results["status"] == "success"
    assert "expected_impact" in results
    assert results["bundle_id"] == str(bundle.id)
