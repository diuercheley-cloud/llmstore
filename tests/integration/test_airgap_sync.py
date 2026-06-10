import hashlib

import pytest
from app.models.commercial.commercial_governance import CommercialPolicyBundle
from app.services.governance.airgap_sync import (
    create_airgap_package,
    export_airgap_package,
    import_airgap_package,
    verify_airgap_manifest,
)
from app.services.governance.policy_federation import PolicyFederationService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_export_verify_import_airgap_package(session: AsyncSession, settings):
    settings.commercial_airgap_sync_enabled = True
    settings.commercial_airgap_sync_mode = "dry_run"

    package = await create_airgap_package(
        session,
        package_type="policy_bundle",
        payload={"policy": "bundle", "api_key": "sk-secret"},
        source_cluster_id="cluster-a",
        target_cluster_id="cluster-b",
        package_version="37.0",
        classification="sovereign_restricted",
        chain_of_custody_json={"events": [{"actor": "ops", "action": "sealed", "timestamp": "2026-05-15T00:00:00Z"}]},
    )
    exported = await export_airgap_package(
        session,
        package.id,
        payload={"policy": "bundle", "api_key": "sk-secret"},
        classification="sovereign_restricted",
    )

    assert exported["dry_run"] is True
    assert "payload.enc" in exported["files"]
    assert "payload.json" not in exported["files"]

    manifest = exported["files"]["manifest.json"]
    expected_hash = hashlib.sha256(
        __import__("json").dumps({k: v for k, v in manifest.items() if k != "manifest_hash"}, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    assert manifest["manifest_hash"] == expected_hash

    verification = await verify_airgap_manifest(session, exported)
    assert verification["valid"] is True

    imported = await import_airgap_package(session, exported)
    assert imported.status == "verified"
    assert "sk-secret" not in exported["files"]["payload.enc"]


@pytest.mark.asyncio
async def test_import_invalid_signature_rejected(session: AsyncSession, settings):
    settings.commercial_airgap_sync_enabled = True
    package = await create_airgap_package(
        session,
        package_type="audit_trail",
        payload={"entry": "ok"},
        source_cluster_id="cluster-a",
        package_version="37.0",
        chain_of_custody_json={"events": [{"actor": "custodian", "action": "handoff", "timestamp": "2026-05-15T00:00:00Z"}]},
    )
    exported = await export_airgap_package(session, package.id, payload={"entry": "ok"})
    exported["files"]["signature.txt"] = "tampered"

    with pytest.raises(ValueError, match="Invalid manifest signature"):
        await import_airgap_package(session, exported)


@pytest.mark.asyncio
async def test_chain_of_custody_required(session: AsyncSession):
    with pytest.raises(ValueError, match="Chain of custody events required"):
        await create_airgap_package(
            session,
            package_type="evidence",
            payload={"doc": "x"},
            source_cluster_id="cluster-a",
            package_version="37.0",
            chain_of_custody_json={},
        )


@pytest.mark.asyncio
async def test_sovereign_restricted_blocks_online_federation_and_allows_encrypted_airgap(
    session: AsyncSession,
):
    service = PolicyFederationService()
    await service.register_governance_peer(
        session,
        peer_cluster_id="peer-a",
        environment="local",
        sync_mode="manual",
    )
    bundle = CommercialPolicyBundle(
        bundle_name="Sovereign Policy",
        bundle_version="37.0",
        bundle_type="operational",
        mode="dry_run",
        status="published",
        rules_json={"classification": "sovereign_restricted"},
        metadata_json={"classification": "sovereign_restricted"},
        immutable_hash="abc123sovereign",
    )
    session.add(bundle)
    await session.flush()

    with pytest.raises(ValueError, match="Sovereign restricted bundles cannot be exported via online federation"):
        await service.export_policy_bundle_for_peer(session, bundle.id, "peer-a")

    package = await create_airgap_package(
        session,
        package_type="policy_bundle",
        payload={"classification": "sovereign_restricted", "bundle": bundle.bundle_name},
        source_cluster_id="cluster-a",
        target_cluster_id="cluster-b",
        package_version="37.0",
        classification="sovereign_restricted",
        chain_of_custody_json={"events": [{"actor": "ops", "action": "sealed", "timestamp": "2026-05-15T00:00:00Z"}]},
    )
    exported = await export_airgap_package(
        session,
        package.id,
        payload={"classification": "sovereign_restricted", "bundle": bundle.bundle_name},
        classification="sovereign_restricted",
    )
    assert "payload.enc" in exported["files"]
