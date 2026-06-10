import pytest
from app.services.security.runtime_attestation import (
    compute_trust_score,
    create_runtime_attestation,
    verify_runtime_attestation,
)
from app.services.security.runtime_integrity import (
    block_untrusted_runtimes,
    create_attestation_policy,
    evaluate_attestation_against_policy,
    measure_loaded_models_integrity,
    require_attestation_for_sensitive_tenants,
    summarize_integrity_status,
    verify_inference_adapter_integrity,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_attestation_policy(session: AsyncSession):
    policy = await create_attestation_policy(
        session,
        policy_name="test-policy",
        policy_version="1.0",
        min_trust_score=0.5,
        max_drift_threshold=0.2,
        require_signed_evidence=True,
        require_measurement_chain=True,
        require_model_binding=True,
        require_workflow_binding=False,
        allowed_enclave_types=["tpm_placeholder", "sev_placeholder"],
        allowed_platform_types=["linux_x86_64"],
        enforcement_mode="enforce",
        block_untrusted=True,
    )
    assert policy.id is not None
    assert policy.policy_hash
    assert policy.is_active is True
    assert policy.policy_name == "test-policy"


@pytest.mark.asyncio
async def test_evaluate_attestation_against_policy(session: AsyncSession):
    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-a",
        model_hash="model_hash",
        enclave_type="tpm_placeholder",
    )
    await verify_runtime_attestation(session, record.id)
    await compute_trust_score(session, record.id)

    policy = await create_attestation_policy(
        session,
        policy_name="strict-policy",
        min_trust_score=0.0,
        allowed_enclave_types=["tpm_placeholder"],
        enforcement_mode="enforce",
    )

    result = await evaluate_attestation_against_policy(session, record.id, policy.id)
    assert result["passed"] is True


@pytest.mark.asyncio
async def test_evaluate_attestation_fails_policy(session: AsyncSession):
    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-b",
        enclave_type="software_attested",
    )
    await compute_trust_score(session, record.id)

    policy = await create_attestation_policy(
        session,
        policy_name="hw-only-policy",
        allowed_enclave_types=["tpm_placeholder"],
        enforcement_mode="enforce",
    )

    result = await evaluate_attestation_against_policy(session, record.id, policy.id)
    assert result["passed"] is False
    assert any("enclave_type_not_allowed" in r for r in result["reasons"])


@pytest.mark.asyncio
async def test_block_untrusted_runtimes(session: AsyncSession):
    record = await create_runtime_attestation(session, cluster_id="cluster-c")
    await verify_runtime_attestation(session, record.id)

    result = await block_untrusted_runtimes(session, cluster_id="cluster-c", mode="report_only")
    assert result["allowed"] is True

    await create_runtime_attestation(
        session, cluster_id="cluster-c", node_id="untrusted-node"
    )


@pytest.mark.asyncio
async def test_measure_loaded_models_integrity(session: AsyncSession):
    record = await create_runtime_attestation(session, cluster_id="cluster-d")

    models = [
        {"model_id": "model-a", "expected_hash": "abc", "observed_hash": "abc"},
        {"model_id": "model-b", "expected_hash": "def", "observed_hash": "xyz"},
    ]
    results = await measure_loaded_models_integrity(
        session,
        cluster_id="cluster-d",
        model_hashes=models,
        attestation_id=record.id,
    )
    assert len(results) == 2
    assert results[0]["drift_detected"] is False
    assert results[1]["drift_detected"] is True

    await session.refresh(record)
    assert record.drift_detected is True


@pytest.mark.asyncio
async def test_verify_inference_adapter_integrity(session: AsyncSession):
    result = await verify_inference_adapter_integrity(
        session,
        cluster_id="cluster-e",
        adapter_name="openai-adapter",
        expected_hash="abc",
        observed_hash="abc",
    )
    assert result["drift_detected"] is False
    assert result["status"] == "valid"

    result2 = await verify_inference_adapter_integrity(
        session,
        cluster_id="cluster-f",
        adapter_name="openai-adapter",
        expected_hash="abc",
        observed_hash="xyz",
    )
    assert result2["drift_detected"] is True
    assert result2["status"] == "drift"


@pytest.mark.asyncio
async def test_summarize_integrity_status(session: AsyncSession):
    await create_runtime_attestation(session, cluster_id="cluster-g")
    await create_runtime_attestation(session, cluster_id="cluster-h")

    summary = await summarize_integrity_status(session)
    assert summary["total_attestations"] >= 2
    assert summary["active_policies"] >= 0


@pytest.mark.asyncio
async def test_require_attestation_for_sensitive_tenants(session: AsyncSession):
    result = await require_attestation_for_sensitive_tenants(
        session,
        tenant_id="sensitive-tenant-1",
        cluster_id="cluster-i",
    )
    assert result["required"] is False
    assert result["reason"] == "feature_disabled"
