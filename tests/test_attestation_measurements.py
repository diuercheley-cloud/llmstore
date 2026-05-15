import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security.attestation_measurements import (
    snapshot_runtime_measurement,
    snapshot_loaded_models,
    snapshot_workflow_hash,
    snapshot_policy_bundle,
    snapshot_routing_hash,
    snapshot_runtime_binary,
    snapshot_environment_fingerprint,
    get_measurement_history,
    summarize_measurements,
)


@pytest.mark.asyncio
async def test_snapshot_runtime_measurement(session: AsyncSession):
    record = await snapshot_runtime_measurement(
        session,
        cluster_id="cluster-a",
        node_id="node-1",
        measurement_type="runtime_binary",
        object_name="/usr/local/bin/inference",
        object_version="1.0.0",
    )
    assert record.id is not None
    assert record.measurement_hash
    assert record.status == "valid"
    assert record.drift_detected is False


@pytest.mark.asyncio
async def test_snapshot_measurement_with_drift(session: AsyncSession):
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"test content")
        tmp_path = f.name
    try:
        record = await snapshot_runtime_measurement(
            session,
            cluster_id="cluster-b",
            measurement_type="runtime_binary",
            object_path=tmp_path,
            expected_hash="wrong_expected_hash_placeholder",
        )
        assert record.status == "drift"
        assert record.drift_detected is True
        assert "hash_mismatch" in record.drift_reasons_json
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_snapshot_loaded_models(session: AsyncSession):
    models = [
        {"name": "model-a", "version": "1.0", "path": "/models/a.gguf", "expected_hash": "abc"},
        {"name": "model-b", "version": "2.0", "path": "/models/b.gguf", "expected_hash": "def"},
    ]
    records = await snapshot_loaded_models(
        session,
        cluster_id="cluster-c",
        model_paths=models,
    )
    assert len(records) == 2
    for r in records:
        assert r.measurement_type == "loaded_model"


@pytest.mark.asyncio
async def test_snapshot_workflow_hash(session: AsyncSession):
    record = await snapshot_workflow_hash(
        session,
        cluster_id="cluster-d",
        workflow_id="wf-001",
        workflow_hash="wf_hash_abc",
    )
    assert record.measurement_type == "workflow_hash"
    assert record.object_name == "wf-001"


@pytest.mark.asyncio
async def test_snapshot_policy_bundle(session: AsyncSession):
    record = await snapshot_policy_bundle(
        session,
        cluster_id="cluster-e",
        bundle_name="governance-policy-v1",
        bundle_hash="policy_hash_abc",
    )
    assert record.measurement_type == "policy_bundle"


@pytest.mark.asyncio
async def test_snapshot_routing_hash(session: AsyncSession):
    record = await snapshot_routing_hash(
        session,
        cluster_id="cluster-f",
        routing_id="router-1",
        routing_hash="routing_hash_abc",
    )
    assert record.measurement_type == "routing_hash"


@pytest.mark.asyncio
async def test_snapshot_runtime_binary(session: AsyncSession):
    record = await snapshot_runtime_binary(
        session,
        cluster_id="cluster-g",
        binary_path="/usr/bin/python3",
        binary_version="3.11.0",
    )
    assert record.measurement_type == "runtime_binary"


@pytest.mark.asyncio
async def test_snapshot_environment_fingerprint(session: AsyncSession):
    record = await snapshot_environment_fingerprint(
        session,
        cluster_id="cluster-h",
        node_id="node-1",
    )
    assert record.measurement_type == "environment_fingerprint"
    assert record.environment_fingerprint
    assert record.status == "valid"


@pytest.mark.asyncio
async def test_get_measurement_history(session: AsyncSession):
    await snapshot_runtime_measurement(session, cluster_id="cluster-i", measurement_type="runtime_binary")
    await snapshot_runtime_measurement(session, cluster_id="cluster-i", measurement_type="policy_bundle")

    history = await get_measurement_history(session, cluster_id="cluster-i")
    assert len(history) == 2

    filtered = await get_measurement_history(session, measurement_type="policy_bundle")
    assert len(filtered) >= 1


@pytest.mark.asyncio
async def test_summarize_measurements(session: AsyncSession):
    await snapshot_runtime_measurement(session, cluster_id="cluster-j")
    await snapshot_runtime_measurement(session, cluster_id="cluster-k")

    summary = await summarize_measurements(session)
    assert summary["total_measurements"] >= 2
