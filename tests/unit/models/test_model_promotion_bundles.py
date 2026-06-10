import pytest
from app.models.commercial.commercial_model_supply_chain import CommercialModelPromotionBundle
from app.services.models.model_promotion_bundles import (
    create_model_promotion_bundle,
    promote_model_from_bundle,
    reject_model_bundle,
    verify_model_promotion_bundle,
)
from app.services.models.model_provenance import create_provenance_attestation
from app.services.models.signed_model_registry import approve_model, register_model_manifest


@pytest.mark.asyncio
async def test_bundle_create_verify_promote_reject(session):
    provenance = await create_provenance_attestation(
        session,
        source_type="airgap",
        source_uri="airgap://cluster-a/model",
        source_cluster_id="cluster-a",
        import_method="airgap",
        artifact_hash="artifact-123",
        evidence_json={"scanner": "offline"},
        chain_of_custody_json={"events": [{"actor": "ops", "action": "sealed", "timestamp": "2026-05-15T00:00:00Z"}]},
    )
    entry = await register_model_manifest(
        session,
        model_name="bundle-model",
        model_alias="bundle-model",
        model_format="api",
        provenance_id=provenance.id,
    )
    await approve_model(session, entry.id, approved_by="ops")

    bundle = await create_model_promotion_bundle(
        session,
        bundle_name="Bundle 38",
        registry_entry_id=entry.id,
        source_cluster_id="cluster-a",
        target_cluster_id="cluster-b",
    )
    verification = await verify_model_promotion_bundle(session, bundle)
    promoted = await promote_model_from_bundle(session, bundle.id, imported_by="airgap-admin")

    rejectable = CommercialModelPromotionBundle(
        bundle_name="Reject 38",
        source_cluster_id="cluster-a",
        target_cluster_id="cluster-b",
        manifest_json={"model": {"checksum_sha256": "x", "manifest_hash": "y"}, "provenance": {"artifact_hash": "z"}, "manifest_hash": "hash"},
        manifest_hash="hash",
        signature=None,
        status="created",
    )
    session.add(rejectable)
    await session.flush()
    rejected = await reject_model_bundle(session, rejectable.id, reason="manual review failed")

    assert verification["valid"] is True
    assert bundle.status == "promoted"
    assert promoted.trust_state == "pending"
    assert rejected.status == "rejected"


@pytest.mark.asyncio
async def test_bundle_endpoints_require_admin_auth(admin_client, admin_token_headers):
    unauthorized = await admin_client.get("/admin/models/supply-chain/bundles")
    assert unauthorized.status_code == 401

    authorized = await admin_client.get("/admin/models/supply-chain/bundles", headers=admin_token_headers)
    assert authorized.status_code == 200
