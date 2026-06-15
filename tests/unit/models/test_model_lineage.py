import pytest
from app.services.models.model_lifecycle_manager import discover_model
from app.services.models.model_lineage import (
    create_lineage_entry,
    get_lineage_dag,
    list_lineage_entries,
    serialize_lineage_entry,
    validate_lineage,
    verify_provenance_chain,
)


@pytest.mark.asyncio
async def test_create_lineage_entry(session):
    record = await discover_model(session, model_name="lineage-model", cluster_id="c1")
    await session.flush()
    entry = await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="a" * 64,
        evidence_json={"source": "usb"},
    )
    await session.commit()
    assert entry.derivation_method == "original_import"
    assert entry.depth == 0
    assert entry.artifact_hash == "a" * 64


@pytest.mark.asyncio
async def test_create_child_lineage_entry(session):
    record = await discover_model(session, model_name="lineage-child-model")
    await session.flush()
    parent = await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="b" * 64,
    )
    await session.flush()
    child = await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        parent_lineage_id=parent.id,
        source_type="finetune",
        derivation_method="finetune_derivative",
        artifact_hash="c" * 64,
        predecessor_hash="b" * 64,
    )
    await session.commit()
    assert child.depth == 1
    assert child.parent_lineage_id == parent.id


@pytest.mark.asyncio
async def test_invalid_derivation_method_raises(session):
    record = await discover_model(session, model_name="bad-derivation")
    await session.flush()
    with pytest.raises(ValueError, match="Invalid derivation method"):
        await create_lineage_entry(
            session,
            lifecycle_record_id=record.id,
            source_type="import",
            derivation_method="invalid_method",
            artifact_hash="d" * 64,
        )


@pytest.mark.asyncio
async def test_get_lineage_dag(session):
    record = await discover_model(session, model_name="dag-model")
    await session.flush()
    p = await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="e" * 64,
    )
    await session.flush()
    c = await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        parent_lineage_id=p.id,
        source_type="finetune",
        derivation_method="finetune_derivative",
        artifact_hash="f" * 64,
        predecessor_hash="e" * 64,
    )
    await session.flush()
    dag = await get_lineage_dag(session, record.id)
    assert len(dag["nodes"]) == 2
    assert len(dag["edges"]) == 1
    assert dag["depth"] == 1
    assert dag["total_entries"] == 2


@pytest.mark.asyncio
async def test_validate_lineage(session):
    record = await discover_model(session, model_name="valid-lineage")
    await session.flush()
    await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="g" * 64,
    )
    await session.flush()
    result = await validate_lineage(session, record.id)
    assert result["valid"] is True
    assert result["entries_checked"] == 1


@pytest.mark.asyncio
async def test_validate_lineage_empty(session):
    record = await discover_model(session, model_name="no-lineage")
    await session.flush()
    result = await validate_lineage(session, record.id)
    assert result["valid"] is False
    assert result["reason"] == "no_lineage_entries"


@pytest.mark.asyncio
async def test_verify_provenance_chain(session):
    from app.services.models.model_provenance import create_provenance_attestation

    provenance = await create_provenance_attestation(
        session,
        source_type="airgap",
        source_uri="airgap://c1/m",
        source_cluster_id="c1",
        import_method="airgap",
        artifact_hash="prov-chain-hash",
    )
    await session.flush()
    record = await discover_model(
        session,
        model_name="prov-chain-model",
        provenance_id=provenance.id,
    )
    await session.flush()
    await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="h" * 64,
        provenance_id=provenance.id,
    )
    await session.flush()
    result = await verify_provenance_chain(session, record.id)
    assert result["valid"] is True
    assert result["provenance_linked"] is True
    assert result["chain_length"] >= 1


@pytest.mark.asyncio
async def test_list_lineage_entries(session):
    record = await discover_model(session, model_name="list-lineage")
    await session.flush()
    await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="i" * 64,
    )
    await session.flush()
    entries = await list_lineage_entries(session, lifecycle_record_id=record.id, limit=10)
    assert len(entries) >= 1


@pytest.mark.asyncio
async def test_serialize_lineage_entry(session):
    record = await discover_model(session, model_name="ser-lineage")
    await session.flush()
    entry = await create_lineage_entry(
        session,
        lifecycle_record_id=record.id,
        source_type="import",
        derivation_method="original_import",
        artifact_hash="j" * 64,
    )
    await session.flush()
    data = serialize_lineage_entry(entry)
    assert data["derivation_method"] == "original_import"
    assert len(data["artifact_hash"]) == 12
    data_full = serialize_lineage_entry(entry, sensitive=True)
    assert len(data_full["artifact_hash"]) == 64
