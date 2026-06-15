import pytest
from app.services.security.runtime_attestation import (
    attestation_chaining,
    collect_enclave_evidence,
    compute_trust_score,
    create_runtime_attestation,
    detect_drift,
    revoke_attestation,
    sev_placeholder,
    sgx_placeholder,
    software_attested,
    summarize_attestation_status,
    tpm_placeholder,
    vbs_placeholder,
    verify_runtime_attestation,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_runtime_attestation(session: AsyncSession):
    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-a",
        node_id="node-1",
        tenant_id="tenant-1",
        runtime_hash=None,
        firmware_hash="firmware_hash_abc",
        model_hash="model_hash_abc",
        workflow_hash="workflow_hash_abc",
        policy_hash="policy_hash_abc",
    )
    assert record.id is not None
    assert record.runtime_hash
    assert record.evidence_hash
    assert record.immutable_hash
    assert record.cluster_id == "cluster-a"
    assert record.node_id == "node-1"
    assert record.tenant_id == "tenant-1"
    assert record.status == "pending"
    assert record.trusted is False
    assert record.drift_detected is False


@pytest.mark.asyncio
async def test_verify_runtime_attestation(session: AsyncSession):
    record = await create_runtime_attestation(session, cluster_id="cluster-b")
    assert record.status == "pending"

    verified = await verify_runtime_attestation(session, record.id)
    assert verified.status == "trusted"
    assert verified.trusted is True
    assert verified.verified_at is not None


@pytest.mark.asyncio
async def test_verify_expired_attestation(session: AsyncSession):
    from datetime import timedelta

    from app.core.time import utc_now

    record = await create_runtime_attestation(session, cluster_id="cluster-c")
    record.expires_at = utc_now() - timedelta(seconds=1)
    await session.flush()

    verified = await verify_runtime_attestation(session, record.id)
    assert verified.status == "expired"
    assert verified.trusted is False


@pytest.mark.asyncio
async def test_compute_trust_score(session: AsyncSession):
    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-d",
        enclave_type="tpm_placeholder",
    )
    score = await compute_trust_score(session, record.id)
    assert 0.0 <= score <= 1.0

    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-e",
        enclave_type="software_attested",
    )
    software_score = await compute_trust_score(session, record.id)
    assert software_score >= 0.0


@pytest.mark.asyncio
async def test_detect_drift(session: AsyncSession):
    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-f",
        model_hash="original_model_hash",
        workflow_hash="original_workflow_hash",
    )
    drift_result = await detect_drift(
        session,
        record.id,
        runtime_hash="different_runtime_hash",
        model_hash="different_model_hash",
        workflow_hash="different_workflow_hash",
    )
    assert drift_result["drift_detected"] is True
    assert len(drift_result["drift_reasons"]) >= 2

    record2 = await create_runtime_attestation(
        session,
        cluster_id="cluster-g",
        model_hash="same_hash",
    )
    no_drift = await detect_drift(
        session,
        record2.id,
        model_hash="same_hash",
    )
    assert no_drift["drift_detected"] is False


@pytest.mark.asyncio
async def test_attestation_chaining(session: AsyncSession):
    record = await create_runtime_attestation(session, cluster_id="cluster-h")
    chain_hash = await attestation_chaining(session, record.id)
    assert chain_hash
    assert record.measurement_chain_hash == chain_hash


@pytest.mark.asyncio
async def test_revoke_attestation(session: AsyncSession):
    record = await create_runtime_attestation(session, cluster_id="cluster-i")
    revoked = await revoke_attestation(session, record.id, reason="security_audit")
    assert revoked.status == "revoked"
    assert revoked.trusted is False
    assert revoked.revoked_at is not None
    assert revoked.metadata_json.get("revocation_reason") == "security_audit"


@pytest.mark.asyncio
async def test_summarize_attestation_status(session: AsyncSession):
    await create_runtime_attestation(session, cluster_id="cluster-j")
    await create_runtime_attestation(session, cluster_id="cluster-k")

    summary = await summarize_attestation_status(session)
    assert summary["total_attestations"] >= 2


@pytest.mark.asyncio
async def test_enclave_placeholders():
    tpm = tpm_placeholder()
    assert tpm["enclave"] == "tpm_placeholder"
    assert tpm["boot_healthy"] is True

    sev = sev_placeholder()
    assert sev["enclave"] == "sev_placeholder"

    sgx = sgx_placeholder()
    assert sgx["enclave"] == "sgx_placeholder"
    assert sgx["prod"] is True
    assert sgx["debug"] is False

    vbs = vbs_placeholder()
    assert vbs["enclave"] == "vbs_placeholder"
    assert vbs["secure_kernel"] is True

    sw = software_attested()
    assert sw["enclave"] == "software_attested"
    assert "fingerprint" in sw


@pytest.mark.asyncio
async def test_collect_enclave_evidence():
    for enclave in (
        "tpm_placeholder",
        "sev_placeholder",
        "sgx_placeholder",
        "vbs_placeholder",
        "software_attested",
    ):
        evidence = collect_enclave_evidence(enclave)
        assert evidence["enclave"] == enclave
