import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.commercial_governance import CommercialPolicyBundle
from app.services.governance.airgap_sync import create_airgap_package, export_airgap_package
from app.services.governance.policy_federation import PolicyFederationService
from app.services.security.offline_crl import (
    apply_offline_crl,
    create_offline_crl,
    is_bundle_revoked,
    is_key_revoked,
    is_peer_revoked,
)
from app.services.security.tenant_encryption import TenantEncryptionService


@pytest.mark.asyncio
async def test_offline_crl_revokes_key_bundle_peer_and_export(
    session: AsyncSession,
    settings,
):
    client = Client(name=f"tenant-{uuid.uuid4()}")
    session.add(client)
    await session.flush()

    encryption = TenantEncryptionService(settings)
    key = await encryption.create_tenant_key(session, client.id, "export")

    bundle = CommercialPolicyBundle(
        bundle_name="Bundle CRL",
        bundle_version="1.0",
        bundle_type="operational",
        mode="dry_run",
        status="published",
        rules_json={"hello": "world"},
        metadata_json={},
        immutable_hash="bundlehash-1",
    )
    session.add(bundle)

    federation = PolicyFederationService()
    await federation.register_governance_peer(
        session,
        peer_cluster_id="peer-revoke",
        environment="local",
        sync_mode="manual",
    )

    package = await create_airgap_package(
        session,
        package_type="policy_bundle",
        payload={"bundle": "Bundle CRL"},
        source_cluster_id="cluster-a",
        package_version="37.0",
        chain_of_custody_json={"events": [{"actor": "ops", "action": "sealed", "timestamp": "2026-05-15T00:00:00Z"}]},
    )
    exported = await export_airgap_package(session, package.id, payload={"bundle": "Bundle CRL"})

    crl = await create_offline_crl(
        session,
        crl_version="37.0",
        revoked_key_fingerprints_json=[key.key_fingerprint],
        revoked_bundle_hashes_json=[bundle.immutable_hash, exported["files"]["manifest.json"]["manifest_hash"]],
        revoked_peer_ids_json=["peer-revoke"],
        reason="validation",
    )
    result = await apply_offline_crl(session, crl.id)

    assert result["revoked_keys"] >= 1
    assert result["revoked_bundles"] >= 1
    assert result["revoked_peers"] >= 1
    assert await is_key_revoked(session, key.key_fingerprint) is True
    assert await is_bundle_revoked(session, bundle.immutable_hash) is True
    assert await is_peer_revoked(session, "peer-revoke") is True


@pytest.mark.asyncio
async def test_offline_crl_helpers_false_when_not_revoked(session: AsyncSession):
    crl = await create_offline_crl(session, crl_version="empty")
    assert crl.signature
    assert await is_key_revoked(session, "nope") is False
    assert await is_bundle_revoked(session, "nope") is False
    assert await is_peer_revoked(session, "nope") is False
