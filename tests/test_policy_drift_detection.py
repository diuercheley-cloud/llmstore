import pytest
from app.services.governance.policy_engine import PolicyEngineService
from app.services.governance.policy_registry import PolicyRegistryService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_detect_policy_drift_missing_bundle(session: AsyncSession):
    service = PolicyEngineService()
    
    # No active bundle for 'qos'
    drifts = await service.detect_policy_drift(session, "qos")
    
    assert len(drifts) == 1
    assert drifts[0].drift_type == "missing_rule"
    assert drifts[0].severity == "medium"

@pytest.mark.asyncio
async def test_detect_policy_drift_config_mismatch(session: AsyncSession):
    engine = PolicyEngineService()
    registry = PolicyRegistryService()
    
    rules = {"routing": {"force_local_only": True}}
    bundle = await registry.create_policy_bundle(session, "Drift Test", "1.0", "routing", rules)
    await registry.publish_policy_bundle(session, bundle.id, "admin")
    await registry.activate_policy_bundle(session, bundle.id, "admin")
    
    # Runtime config matches
    drifts = await engine.detect_policy_drift(session, "routing", runtime_config=rules)
    assert len(drifts) == 0
    
    # Runtime config differs
    runtime_config = {"routing": {"force_local_only": False}}
    drifts = await engine.detect_policy_drift(session, "routing", runtime_config=runtime_config)
    
    assert len(drifts) == 1
    assert drifts[0].drift_type == "config_drift"
    assert drifts[0].severity == "high"
    assert drifts[0].bundle_id == bundle.id
