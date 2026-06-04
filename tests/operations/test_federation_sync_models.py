import pytest
from app.models.client import Client
from app.models.operations.federation_sync import (
    FederationConflictResolution,
    FederationLineageLink,
    FederationSynchronizationBundle,
    FederationSynchronizationReceipt,
    FederationSynchronizationSession,
    FederationTrustNegotiation,
    SovereignFederationEnvironment,
)
from app.utils.crypto_signer import sign_payload
from sqlalchemy import select


@pytest.mark.asyncio
async def test_federation_sync_models_persist(session):
    client = Client(name="phase77-models")
    session.add(client)
    await session.flush()

    source = SovereignFederationEnvironment(
        id="env-source",
        client_id=client.id,
        environment_name="source",
        environment_type="airgap_node",
        federation_scope="ops",
        trust_level="trusted",
        environment_hash="a" * 64,
        immutable_hash="b" * 64,
    )
    target = SovereignFederationEnvironment(
        id="env-target",
        client_id=client.id,
        environment_name="target",
        environment_type="offline_staging",
        federation_scope="ops",
        trust_level="verified",
        environment_hash="c" * 64,
        immutable_hash="d" * 64,
    )
    sync = FederationSynchronizationSession(
        id="session-1",
        client_id=client.id,
        source_environment_id=source.id,
        target_environment_id=target.id,
        sync_scope="ops",
        session_hash="e" * 64,
        immutable_hash="f" * 64,
    )
    bundle = FederationSynchronizationBundle(
        id="bundle-1",
        client_id=client.id,
        session_id=sync.id,
        bundle_name="bundle",
        bundle_type="mixed",
        bundle_hash="1" * 64,
        lineage_hash="2" * 64,
        parent_bundle_hash=None,
        replay_hash="1" * 64,
        immutable_hash="3" * 64,
    )
    negotiation = FederationTrustNegotiation(
        id="neg-1",
        client_id=client.id,
        source_environment_id=source.id,
        target_environment_id=target.id,
        negotiation_status="accepted",
        required_trust_level="verified",
        negotiated_trust_level="verified",
        immutable_hash="4" * 64,
    )
    conflict = FederationConflictResolution(
        id="conf-1",
        client_id=client.id,
        session_id=sync.id,
        conflict_type="bundle_hash_conflict",
        resolution_strategy="reject",
        resolution_status="resolved",
        replay_safe=False,
        immutable_hash="5" * 64,
    )
    receipt = FederationSynchronizationReceipt(
        id="rec-1",
        client_id=client.id,
        session_id=sync.id,
        receipt_type="sync_session_receipt",
        payload_hash="6" * 64,
        immutable_hash="7" * 64,
        signature=sign_payload("sync"),
    )
    lineage = FederationLineageLink(
        id="link-1",
        client_id=client.id,
        bundle_id=bundle.id,
        parent_bundle_hash=None,
        lineage_hash="8" * 64,
        replay_verifiable=True,
        immutable_hash="9" * 64,
    )
    session.add_all([source, target, sync, bundle, negotiation, conflict, receipt, lineage])
    await session.commit()

    stored = (await session.execute(select(FederationSynchronizationSession))).scalar_one()
    assert stored.replay_verifiable is True
    assert stored.offline_verifiable is True
    assert source.offline_only is True


def test_phase_77_migration_presence():
    content = open("control_plane/alembic/versions/phase77_federation_sync_protocol.py", "r", encoding="utf-8").read()
    assert "sovereign_federation_environments" in content
    assert "federation_synchronization_sessions" in content
    assert "federation_lineage_links" in content
