
import pytest
from app.models.client import Client
from app.models.operations.attestation_framework import (
    AttestationChainLink,
    AttestationFederationBundle,
    AttestationReceipt,
    AttestationTrustPolicy,
    AttestationVerificationResult,
    SovereignExecutionAttestation,
)
from app.utils.crypto_signer import sign_payload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_attestation_framework_models_persist(session: AsyncSession):
    client = Client(name="phase76-models")
    session.add(client)
    await session.flush()

    attestation = SovereignExecutionAttestation(
        id="att-1",
        client_id=client.id,
        attestation_type="workflow",
        subject_type="workflow",
        subject_ref="wf-1",
        attestation_scope="operations",
        attestation_status="issued",
        deterministic_version="v1",
        payload_hash="a" * 64,
        attestation_hash="b" * 64,
        previous_attestation_hash=None,
        signature=sign_payload("workflow"),
        attestation_chain_position="1",
        immutable_hash="c" * 64,
    )
    policy = AttestationTrustPolicy(
        id="pol-1",
        client_id=client.id,
        policy_name="default",
        allowed_attestation_types_json={"allowed": ["workflow"]},
        immutable_hash="d" * 64,
    )
    bundle = AttestationFederationBundle(
        id="bun-1",
        client_id=client.id,
        bundle_name="bundle",
        bundle_scope="operations",
        bundle_hash="e" * 64,
        source_environment="source",
        target_environment="target",
        immutable_hash="f" * 64,
    )
    verification = AttestationVerificationResult(
        id="ver-1",
        client_id=client.id,
        attestation_id=attestation.id,
        verification_type="attestation",
        verification_status="passed",
        verification_summary="ok",
        replay_verified=True,
        chain_verified=True,
        offline_verified=True,
        immutable_hash="1" * 64,
    )
    receipt = AttestationReceipt(
        id="rec-1",
        client_id=client.id,
        attestation_id=attestation.id,
        receipt_type="attestation_receipt",
        payload_hash="2" * 64,
        immutable_hash="3" * 64,
        signature=sign_payload("receipt"),
    )
    chain_link = AttestationChainLink(
        id="lnk-1",
        client_id=client.id,
        attestation_id=attestation.id,
        previous_link_hash=None,
        current_link_hash="4" * 64,
        chain_position="1",
        replay_verifiable=True,
        immutable_hash="5" * 64,
    )
    session.add_all([attestation, policy, bundle, verification, receipt, chain_link])
    await session.commit()

    stored = (await session.execute(select(SovereignExecutionAttestation))).scalars().all()
    assert stored[0].replay_verifiable is True
    assert stored[0].offline_verifiable is True
    assert stored[0].signature.startswith("placeholder-signature:")
    assert bundle.bundle_status == "draft"
    assert policy.require_chain_integrity is True


def test_phase_76_migration_presence():
    migration_path = "control_plane/alembic/versions/phase76_attestation_framework.py"
    content = open(migration_path, "r", encoding="utf-8").read()
    assert "sovereign_execution_attestations" in content
    assert "attestation_trust_policies" in content
    assert "attestation_federation_bundles" in content
