import pytest
from app.models.commercial.commercial_governance_federation import (
    CommercialFederatedPolicySync,
)
from app.services.governance.governance_consistency import GovernanceConsistencyService
from app.services.governance.policy_federation import PolicyFederationService
from app.services.governance.policy_registry import PolicyRegistryService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_compare_active_policies_across_clusters(session: AsyncSession):
    registry = PolicyRegistryService()
    bundle = await registry.create_policy_bundle(
        db=session,
        bundle_name="Routing Policy",
        bundle_version="1.0",
        bundle_type="routing",
        rules_json={"routing": {"max_cost": 0.5}},
    )
    bundle.status = "active"
    await session.flush()

    federation = PolicyFederationService()
    await federation.register_governance_peer(
        db=session, peer_cluster_id="peer-a", environment="production"
    )

    sync = CommercialFederatedPolicySync(
        source_cluster_id="peer-a",
        target_cluster_id="local",
        bundle_name="Routing Policy",
        bundle_version="1.0",
        sync_direction="inbound",
        status="success",
        source_hash=bundle.immutable_hash,
    )
    session.add(sync)
    await session.flush()

    service = GovernanceConsistencyService()
    comparisons = await service.compare_active_policies_across_clusters(session, "peer-a")
    assert len(comparisons) >= 1

    for comp in comparisons:
        if comp["bundle_name"] == "Routing Policy":
            assert comp["consistent"] is True
            assert "match" in comp["notes"][0]


@pytest.mark.asyncio
async def test_detect_cross_region_drift(session: AsyncSession):
    federation = PolicyFederationService()
    await federation.register_governance_peer(
        db=session,
        peer_cluster_id="peer-offline",
        environment="production",
        status="offline",
        region="us-west",
    )
    await federation.register_governance_peer(
        db=session,
        peer_cluster_id="peer-online",
        environment="production",
        status="active",
        region="eu-central",
    )

    registry = PolicyRegistryService()
    bundle = await registry.create_policy_bundle(
        db=session,
        bundle_name="Test",
        bundle_version="1.0",
        bundle_type="routing",
        rules_json={"r": 1},
    )
    bundle.status = "active"
    await session.flush()

    sync = CommercialFederatedPolicySync(
        source_cluster_id="peer-online",
        target_cluster_id="local",
        bundle_name="Test",
        bundle_version="1.0",
        sync_direction="inbound",
        status="conflict",
        source_hash="remote-hash",
        target_hash=bundle.immutable_hash,
        conflict_reason="Hash mismatch",
    )
    session.add(sync)
    await session.flush()

    service = GovernanceConsistencyService()
    drifts = await service.detect_cross_region_drift(session)
    assert len(drifts) >= 1

    offline_drifts = [d for d in drifts if d["drift_type"] == "peer_offline"]
    conflict_drifts = [d for d in drifts if d["drift_type"] == "policy_conflict"]
    assert len(offline_drifts) >= 1
    assert len(conflict_drifts) >= 1


@pytest.mark.asyncio
async def test_check_compliance_consistency(session: AsyncSession):
    federation = PolicyFederationService()
    await federation.register_governance_peer(
        db=session, peer_cluster_id="peer-a", environment="production", status="active"
    )
    await federation.register_governance_peer(
        db=session, peer_cluster_id="peer-off", environment="production", status="offline"
    )

    service = GovernanceConsistencyService()
    result = await service.check_compliance_consistency(session)
    assert "overall_status" in result
    assert result["offline_peers"] >= 1


@pytest.mark.asyncio
async def test_generate_consistency_report(session: AsyncSession):
    federation = PolicyFederationService()
    await federation.register_governance_peer(
        db=session,
        peer_cluster_id="peer-a",
        environment="production",
        region="us-east",
        status="active",
    )
    await federation.register_governance_peer(
        db=session,
        peer_cluster_id="peer-b",
        environment="staging",
        region="eu-west",
        status="active",
    )

    service = GovernanceConsistencyService()
    report = await service.generate_consistency_report(session)
    assert report["local_cluster_id"] is not None
    assert report["summary"]["total_peers"] >= 2
    assert report["summary"]["regions_covered"] >= 2
    assert "region_coverage" in report
    assert "compliance_consistency" in report
    assert "cross_region_drifts" in report
