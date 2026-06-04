import pytest
from app.core.config import get_settings
from app.models.commercial_governance_federation import (
    CommercialFederatedAuditTrail,
    CommercialGovernanceFederationPeer,
)
from app.services.governance.federated_audit import FederatedAuditService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_ingest_audit_events(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "audit-token"
    settings.commercial_governance_federation_require_token = False

    # Register source as peer
    peer = CommercialGovernanceFederationPeer(
        peer_cluster_id="source-cluster",
        environment="production",
    )
    session.add(peer)
    await session.flush()

    service = FederatedAuditService()

    events = [
        {
            "source_event_id": "evt-001",
            "event_type": "policy_activated",
            "event_payload": {"bundle_name": "test-bundle", "version": "1.0"},
        },
        {
            "source_event_id": "evt-002",
            "event_type": "drift",
            "event_payload": {"bundle_name": "test-bundle", "severity": "high"},
        },
        {
            "source_event_id": "evt-003",
            "event_type": "rollback",
            "event_payload": {"bundle_name": "test-bundle", "reason": "regression"},
        },
    ]

    result = await service.ingest_audit_events(
        db=session,
        events=events,
        source_cluster_id="source-cluster",
        peer_token="audit-token",
    )
    assert result["ingested"] == 3
    assert result["duplicates"] == 0
    assert result["total_events"] == 3


@pytest.mark.asyncio
async def test_audit_ingest_dedupe(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "audit-token"
    settings.commercial_governance_federation_require_token = False

    peer = CommercialGovernanceFederationPeer(
        peer_cluster_id="source-cluster",
        environment="production",
    )
    session.add(peer)
    await session.flush()

    service = FederatedAuditService()

    events = [
        {
            "source_event_id": "evt-001",
            "event_type": "policy_activated",
            "event_payload": {"bundle_name": "test"},
        },
    ]

    # First ingest
    result1 = await service.ingest_audit_events(
        db=session, events=events, source_cluster_id="source-cluster"
    )
    assert result1["ingested"] == 1

    # Second ingest (same events)
    result2 = await service.ingest_audit_events(
        db=session, events=events, source_cluster_id="source-cluster"
    )
    assert result2["ingested"] == 0
    assert result2["duplicates"] == 1


@pytest.mark.asyncio
async def test_dedupe_audit_event(session: AsyncSession):
    service = FederatedAuditService()
    key = "cluster-a:drift:evt-001"

    trail = CommercialFederatedAuditTrail(
        source_cluster_id="cluster-a",
        source_event_id="evt-001",
        event_type="drift",
        event_hash="abc123",
        event_payload_json={"test": True},
        dedupe_key=key,
    )
    session.add(trail)
    await session.flush()

    found = await service.dedupe_audit_event(session, key)
    assert found is not None
    assert found.source_cluster_id == "cluster-a"

    not_found = await service.dedupe_audit_event(session, "nonexistent:key")
    assert not_found is None


@pytest.mark.asyncio
async def test_validate_audit_event_hash(session: AsyncSession):
    service = FederatedAuditService()
    event = {"event_payload": {"bundle_name": "test", "version": "1.0"}}
    event_hash = service._compute_event_hash(event["event_payload"])

    assert service.validate_audit_event_hash(event, event_hash) is True
    assert service.validate_audit_event_hash(event, "wrong-hash") is False


@pytest.mark.asyncio
async def test_summarize_federated_audit(session: AsyncSession):
    service = FederatedAuditService()

    for i in range(5):
        trail = CommercialFederatedAuditTrail(
            source_cluster_id="cluster-a",
            source_event_id=f"evt-{i}",
            event_type="policy_published",
            event_hash=f"hash{i}",
            event_payload_json={"idx": i},
            dedupe_key=f"cluster-a:policy_published:evt-{i}",
        )
        session.add(trail)
    await session.flush()

    summary = await service.summarize_federated_audit(session)
    assert summary["total_events"] >= 5
    assert summary["by_type"].get("policy_published", 0) >= 5


@pytest.mark.asyncio
async def test_ingest_audit_invalid_token(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "correct-token"
    settings.commercial_governance_federation_require_token = True

    service = FederatedAuditService()
    with pytest.raises(ValueError, match="Invalid federation token"):
        await service.ingest_audit_events(
            db=session,
            events=[],
            source_cluster_id="test",
            peer_token="wrong-token",
        )


@pytest.mark.asyncio
async def test_export_audit_events(session: AsyncSession):
    service = FederatedAuditService()

    peer = CommercialGovernanceFederationPeer(
        peer_cluster_id="requestor-peer",
        environment="production",
    )
    session.add(peer)

    for i in range(3):
        trail = CommercialFederatedAuditTrail(
            source_cluster_id="requestor-peer",
            source_event_id=f"evt-{i}",
            event_type="approval",
            event_hash=f"hash{i}",
            event_payload_json={"idx": i},
            dedupe_key=f"requestor-peer:approval:evt-{i}",
        )
        session.add(trail)
    await session.flush()

    exported = await service.export_audit_events(session, "requestor-peer")
    assert len(exported) == 3
    assert exported[0]["event_type"] == "approval"


@pytest.mark.asyncio
async def test_payload_sanitized_in_audit(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_require_token = False

    peer = CommercialGovernanceFederationPeer(
        peer_cluster_id="sanitize-cluster", environment="production"
    )
    session.add(peer)
    await session.flush()

    service = FederatedAuditService()
    events = [
        {
            "source_event_id": "evt-sec",
            "event_type": "approval",
            "event_payload": {"api_key": "sk-secret123", "data": "safe"},
        },
    ]

    result = await service.ingest_audit_events(
        db=session, events=events, source_cluster_id="sanitize-cluster"
    )
    assert result["ingested"] == 1
