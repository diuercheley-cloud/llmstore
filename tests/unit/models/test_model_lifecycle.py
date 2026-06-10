import pytest
from app.services.models.model_lifecycle_manager import (
    discover_model,
    enforce_lifecycle_gates,
    get_lifecycle_by_model,
    list_lifecycle_records,
    serialize_lifecycle_record,
    stage_model,
    summarize_lifecycle_status,
    transition_lifecycle_state,
    verify_offline_model,
)
from app.services.models.model_provenance import create_provenance_attestation


@pytest.mark.asyncio
async def test_discover_model(session):
    record = await discover_model(
        session,
        model_name="test-model-lifecycle",
        model_alias="test-alias",
        provider="test-provider",
        checksum_sha256="a" * 64,
        cluster_id="cluster-test",
    )
    await session.commit()
    assert record.model_name == "test-model-lifecycle"
    assert record.lifecycle_state == "discovered"
    assert record.cluster_id == "cluster-test"


@pytest.mark.asyncio
async def test_stage_model(session):
    record = await discover_model(session, model_name="stage-target", cluster_id="c1")
    await session.flush()
    staged = await stage_model(session, record.id, staged_by="admin")
    await session.commit()
    assert staged.lifecycle_state == "staged"
    assert staged.previous_lifecycle_state == "discovered"


@pytest.mark.asyncio
async def test_transition_lifecycle_state(session):
    record = await discover_model(session, model_name="transition-model")
    await session.flush()
    staged = await stage_model(session, record.id)
    await session.flush()
    pending = await transition_lifecycle_state(
        session, staged.id, target_state="pending_approval", changed_by="admin"
    )
    await session.commit()
    assert pending.lifecycle_state == "pending_approval"


@pytest.mark.asyncio
async def test_invalid_transition_raises(session):
    record = await discover_model(session, model_name="bad-transition")
    await session.flush()
    with pytest.raises(ValueError, match="Invalid transition"):
        await transition_lifecycle_state(
            session, record.id, target_state="promoted", changed_by="admin"
        )


@pytest.mark.asyncio
async def test_get_lifecycle_by_model(session):
    await discover_model(session, model_name="lookup-model", provider="p1")
    await session.flush()
    found = await get_lifecycle_by_model(session, "lookup-model")
    assert found is not None
    assert found.model_name == "lookup-model"


@pytest.mark.asyncio
async def test_list_lifecycle_records(session):
    await discover_model(session, model_name="list-a")
    await discover_model(session, model_name="list-b")
    await session.flush()
    records = await list_lifecycle_records(session, limit=10)
    assert len(records) >= 2


@pytest.mark.asyncio
async def test_list_filter_by_state(session):
    r = await discover_model(session, model_name="filter-staged")
    await session.flush()
    await stage_model(session, r.id)
    await session.flush()
    staged = await list_lifecycle_records(session, lifecycle_state="staged")
    assert all(rec.lifecycle_state == "staged" for rec in staged)


@pytest.mark.asyncio
async def test_summarize_lifecycle_status(session):
    await discover_model(session, model_name="summary-1")
    await session.flush()
    status = await summarize_lifecycle_status(session)
    assert "total" in status
    assert "state_counts" in status


@pytest.mark.asyncio
async def test_enforce_lifecycle_gates(session):
    record = await discover_model(session, model_name="gated-model")
    await session.flush()
    gates = await enforce_lifecycle_gates(session, record)
    assert "allowed" in gates
    assert "gates" in gates
    assert gates["allowed"] is False


@pytest.mark.asyncio
async def test_verify_offline_model_no_record(session):
    verification = await verify_offline_model(
        session,
        model_name="unknown-offline-model",
        checksum_sha256="b" * 64,
        verification_type="offline_import",
        verified_by="admin",
    )
    await session.commit()
    assert verification.overall_valid is False
    assert verification.model_name == "unknown-offline-model"


@pytest.mark.asyncio
async def test_verify_offline_model_with_record(session):
    provenance = await create_provenance_attestation(
        session,
        source_type="airgap",
        source_uri="airgap://c1/model",
        source_cluster_id="c1",
        import_method="airgap",
        artifact_hash="hash-verify-test",
    )
    await session.flush()
    record = await discover_model(
        session,
        model_name="verify-target",
        provenance_id=provenance.id,
        checksum_sha256="c" * 64,
    )
    record.checksum_verified = True
    record.signature_verified = True
    record.attestation_bound = True
    record.lineage_validated = True
    await session.flush()
    verification = await verify_offline_model(
        session,
        model_name="verify-target",
        lifecycle_record_id=record.id,
        verification_type="usb_media",
        verified_by="ops",
    )
    await session.commit()
    assert verification.overall_valid is True


@pytest.mark.asyncio
async def test_serialize_lifecycle_record(session):
    record = await discover_model(session, model_name="serialize-model", checksum_sha256="d" * 64)
    await session.flush()
    data = serialize_lifecycle_record(record)
    assert data["model_name"] == "serialize-model"
    assert len(data["checksum_sha256"]) == 12
    data_full = serialize_lifecycle_record(record, sensitive=True)
    assert len(data_full["checksum_sha256"]) == 64
