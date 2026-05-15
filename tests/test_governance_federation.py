import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_governance_federation import (
    CommercialGovernanceFederationPeer,
    CommercialFederatedPolicySync,
)
from app.services.governance.policy_federation import PolicyFederationService
from app.services.governance.policy_registry import PolicyRegistryService
from app.services.governance.policy_engine import PolicyEngineService
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_register_governance_peer(session: AsyncSession):
    service = PolicyFederationService()
    peer = await service.register_governance_peer(
        db=session,
        peer_cluster_id="cluster-01",
        environment="production",
        region="us-east-1",
        sync_mode="pull",
        trust_level="trusted",
    )
    assert peer.peer_cluster_id == "cluster-01"
    assert peer.status == "active"
    assert peer.sync_mode == "pull"
    assert peer.trust_level == "trusted"
    assert peer.region == "us-east-1"


@pytest.mark.asyncio
async def test_register_duplicate_peer(session: AsyncSession):
    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="cluster-01", environment="production"
    )
    with pytest.raises(ValueError, match="already registered"):
        await service.register_governance_peer(
            db=session, peer_cluster_id="cluster-01", environment="production"
        )


@pytest.mark.asyncio
async def test_register_peer_invalid_sync_mode(session: AsyncSession):
    service = PolicyFederationService()
    with pytest.raises(ValueError, match="Invalid sync_mode"):
        await service.register_governance_peer(
            db=session, peer_cluster_id="cluster-01", environment="production", sync_mode="invalid"
        )


@pytest.mark.asyncio
async def test_register_peer_invalid_trust_level(session: AsyncSession):
    service = PolicyFederationService()
    with pytest.raises(ValueError, match="Invalid trust_level"):
        await service.register_governance_peer(
            db=session, peer_cluster_id="cluster-01", environment="production", trust_level="super"
        )


@pytest.mark.asyncio
async def test_export_policy_bundle_for_peer(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "test-token"

    registry = PolicyRegistryService()
    rules = {"routing": {"force_local_only": True}}
    bundle = await registry.create_policy_bundle(
        db=session,
        bundle_name="Fed Bundle",
        bundle_version="1.0.0",
        bundle_type="routing",
        rules_json=rules,
    )

    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="peer-a", environment="production"
    )

    exported = await service.export_policy_bundle_for_peer(session, bundle.id, "peer-a")
    assert exported["bundle_name"] == "Fed Bundle"
    assert exported["bundle_version"] == "1.0.0"
    assert "signature" in exported
    assert exported["rules_json"] == rules


@pytest.mark.asyncio
async def test_export_policy_to_disabled_peer(session: AsyncSession):
    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="peer-off", environment="production", status="disabled"
    )

    registry = PolicyRegistryService()
    bundle = await registry.create_policy_bundle(
        db=session, bundle_name="Test", bundle_version="1.0", bundle_type="routing", rules_json={"r": 1}
    )

    with pytest.raises(ValueError, match="is disabled"):
        await service.export_policy_bundle_for_peer(session, bundle.id, "peer-off")


@pytest.mark.asyncio
async def test_ingest_policy_bundle_valid(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "test-token"
    settings.commercial_governance_federation_require_token = True
    settings.commercial_governance_federation_require_signature = True

    engine = PolicyEngineService()
    rules = {"routing": {"force_local_only": True}}
    bundle_hash = PolicyRegistryService.calculate_bundle_hash(rules)
    signature = engine.sign_policy_bundle(rules, bundle_hash, "test-token")

    payload = {
        "bundle_name": "Remote Bundle",
        "bundle_version": "2.0.0",
        "bundle_type": "routing",
        "rules_json": rules,
        "immutable_hash": bundle_hash,
        "mode": "dry_run",
        "status": "published",
        "cluster_id": "remote-cluster",
    }

    service = PolicyFederationService()
    result = await service.ingest_policy_bundle_from_peer(
        db=session,
        payload=payload,
        peer_token="test-token",
        peer_signature=signature,
    )
    assert result["status"] in ("received", "success")


@pytest.mark.asyncio
async def test_ingest_policy_invalid_token(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "correct-token"
    settings.commercial_governance_federation_require_token = True

    service = PolicyFederationService()
    with pytest.raises(ValueError, match="Invalid federation token"):
        await service.ingest_policy_bundle_from_peer(
            db=session,
            payload={"bundle_name": "Test", "bundle_version": "1.0", "rules_json": {}},
            peer_token="wrong-token",
        )


@pytest.mark.asyncio
async def test_ingest_policy_invalid_signature(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "test-token"
    settings.commercial_governance_federation_require_token = True
    settings.commercial_governance_federation_require_signature = True

    service = PolicyFederationService()
    with pytest.raises(ValueError, match="Invalid bundle signature"):
        await service.ingest_policy_bundle_from_peer(
            db=session,
            payload={
                "bundle_name": "Test",
                "bundle_version": "1.0",
                "rules_json": {"r": 1},
                "immutable_hash": "abc123",
            },
            peer_token="test-token",
            peer_signature="bad-signature",
        )


@pytest.mark.asyncio
async def test_detect_policy_conflict(session: AsyncSession):
    registry = PolicyRegistryService()
    rules_a = {"routing": {"force_local_only": True}}
    rules_b = {"routing": {"force_local_only": False}}

    bundle = await registry.create_policy_bundle(
        db=session, bundle_name="Conflict Bundle", bundle_version="1.0", bundle_type="routing", rules_json=rules_a
    )

    service = PolicyFederationService()
    conflict = await service.detect_policy_conflict(
        session, bundle_name="Conflict Bundle", bundle_version="1.0", remote_hash="different-hash-value"
    )
    assert conflict is not None
    assert conflict["conflict"] is True
    assert "Hash mismatch" in conflict["reason"]

    no_conflict = await service.detect_policy_conflict(
        session, bundle_name="Conflict Bundle", bundle_version="1.0", remote_hash=bundle.immutable_hash
    )
    assert no_conflict is not None
    assert no_conflict["conflict"] is False


@pytest.mark.asyncio
async def test_sync_policy_bundle(session: AsyncSession):
    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="sync-peer", environment="production"
    )

    registry = PolicyRegistryService()
    bundle = await registry.create_policy_bundle(
        db=session, bundle_name="Sync Test", bundle_version="1.0", bundle_type="routing", rules_json={"r": 1}
    )

    sync = await service.sync_policy_bundle(session, "sync-peer", bundle.id)
    assert sync.status == "pending"
    assert sync.source_hash == bundle.immutable_hash
    assert sync.bundle_name == "Sync Test"


@pytest.mark.asyncio
async def test_summarize_federation_status(session: AsyncSession):
    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="peer-1", environment="production", region="us-east"
    )
    await service.register_governance_peer(
        db=session, peer_cluster_id="peer-2", environment="staging", region="eu-west"
    )

    summary = await service.summarize_federation_status(session)
    assert summary["total_peers"] == 2
    assert summary["online_peers"] == 2


@pytest.mark.asyncio
async def test_tenant_scoped_bundle_peer_not_authorized(session: AsyncSession):
    settings = get_settings()
    settings.commercial_governance_federation_shared_token = "test-token"
    settings.commercial_governance_federation_require_signature = False
    settings.commercial_governance_federation_require_token = False

    registry = PolicyRegistryService()
    bundle = await registry.create_policy_bundle(
        db=session,
        bundle_name="Tenant Bundle",
        bundle_version="1.0",
        bundle_type="routing",
        rules_json={"r": 1},
        client_id=uuid.uuid4(),
        metadata_json={"allowed_federation_peers": ["authorized-peer"]},
    )

    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="unauthorized-peer", environment="production"
    )

    with pytest.raises(ValueError, match="not authorized"):
        await service.export_policy_bundle_for_peer(session, bundle.id, "unauthorized-peer")


@pytest.mark.asyncio
async def test_payload_sanitized_in_register(session: AsyncSession):
    service = PolicyFederationService()
    meta = {"api_key": "sk-secret123", "normal_key": "safe_value"}
    peer = await service.register_governance_peer(
        db=session,
        peer_cluster_id="sanitized-peer",
        environment="production",
        metadata_json=meta,
    )
    assert peer.metadata_json.get("api_key") == "[REDACTED]"
    assert peer.metadata_json.get("normal_key") == "safe_value"


@pytest.mark.asyncio
async def test_resolve_policy_conflict(session: AsyncSession):
    service = PolicyFederationService()
    await service.register_governance_peer(
        db=session, peer_cluster_id="conflict-peer", environment="production"
    )

    registry = PolicyRegistryService()
    bundle = await registry.create_policy_bundle(
        db=session, bundle_name="Conflict", bundle_version="1.0", bundle_type="routing", rules_json={"r": 1}
    )

    sync = await service.sync_policy_bundle(session, "conflict-peer", bundle.id)
    sync.status = "conflict"
    sync.conflict_reason = "Hash mismatch"
    await session.flush()

    resolved = await service.resolve_policy_conflict(session, sync.id, "accept_remote")
    assert resolved.status == "success"
    assert resolved.completed_at is not None
