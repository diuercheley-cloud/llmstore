import pytest

from app.services.models.model_lifecycle_manager import (
    discover_model,
    stage_model,
    transition_lifecycle_state,
)
from app.services.models.model_promotion import create_promotion_request
from app.services.models.model_quarantine import (
    list_quarantined_models,
    list_rollback_records,
    quarantine_lifecycle_model,
    release_from_quarantine,
    rollback_model,
    serialize_rollback_record,
)


@pytest.mark.asyncio
async def test_quarantine_model(session):
    record = await discover_model(session, model_name="quar-model", cluster_id="c1")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    quarantined = await quarantine_lifecycle_model(
        session, record.id, reason="checksum_mismatch", quarantined_by="scanner"
    )
    await session.commit()
    assert quarantined.lifecycle_state == "quarantined"
    assert quarantined.previous_lifecycle_state == "staged"


@pytest.mark.asyncio
async def test_quarantine_invalid_reason_raises(session):
    record = await discover_model(session, model_name="bad-reason-model")
    await session.flush()
    with pytest.raises(ValueError, match="Invalid quarantine reason"):
        await quarantine_lifecycle_model(session, record.id, reason="invalid_reason")


@pytest.mark.asyncio
async def test_cannot_quarantine_archived(session):
    record = await discover_model(session, model_name="archived-no-quar")
    await session.flush()
    await transition_lifecycle_state(session, record.id, target_state="archived")
    await session.flush()
    with pytest.raises(ValueError, match="Cannot quarantine"):
        await quarantine_lifecycle_model(session, record.id, reason="manual_quarantine")


@pytest.mark.asyncio
async def test_release_from_quarantine(session):
    record = await discover_model(session, model_name="release-model")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    await quarantine_lifecycle_model(session, record.id, reason="manual_quarantine")
    await session.flush()
    released = await release_from_quarantine(
        session, record.id, released_by="admin", target_state="staged", reason="Cleared"
    )
    await session.commit()
    assert released.lifecycle_state == "staged"


@pytest.mark.asyncio
async def test_release_non_quarantined_raises(session):
    record = await discover_model(session, model_name="not-quar-model")
    await session.flush()
    with pytest.raises(ValueError, match="not quarantined"):
        await release_from_quarantine(session, record.id)


@pytest.mark.asyncio
async def test_rollback_model(session):
    record = await discover_model(session, model_name="rollback-model")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    await transition_lifecycle_state(session, record.id, target_state="pending_approval")
    await session.flush()
    rollback = await rollback_model(
        session,
        record.id,
        rollback_to_state="staged",
        rollback_reason="Validation failed",
        rolled_back_by="admin",
    )
    await session.commit()
    assert rollback.rollback_from_state == "pending_approval"
    assert rollback.rollback_to_state == "staged"
    assert rollback.verification_hash is not None


@pytest.mark.asyncio
async def test_rollback_from_invalid_state_raises(session):
    record = await discover_model(session, model_name="bad-rollback")
    await session.flush()
    with pytest.raises(ValueError, match="Cannot rollback"):
        await rollback_model(
            session, record.id, rollback_to_state="staged", rollback_reason="test"
        )


@pytest.mark.asyncio
async def test_rollback_with_predecessor_checksum(session):
    record = await discover_model(
        session, model_name="rollback-checksum", checksum_sha256="x" * 64
    )
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    await transition_lifecycle_state(session, record.id, target_state="pending_approval")
    await session.flush()
    rollback = await rollback_model(
        session,
        record.id,
        rollback_to_state="staged",
        rollback_reason="Revert to previous",
        predecessor_checksum="x" * 64,
    )
    await session.commit()
    assert rollback.checksum_verified is True


@pytest.mark.asyncio
async def test_list_quarantined_models(session):
    r = await discover_model(session, model_name="list-quar")
    await session.flush()
    await stage_model(session, r.id)
    await session.flush()
    await quarantine_lifecycle_model(session, r.id, reason="policy_violation")
    await session.flush()
    quarantined = await list_quarantined_models(session, limit=10)
    assert len(quarantined) >= 1
    assert all(m.lifecycle_state == "quarantined" for m in quarantined)


@pytest.mark.asyncio
async def test_list_rollback_records(session):
    r = await discover_model(session, model_name="list-rollback")
    await session.flush()
    await stage_model(session, r.id)
    await session.flush()
    await transition_lifecycle_state(session, r.id, target_state="pending_approval")
    await session.flush()
    await rollback_model(
        session, r.id, rollback_to_state="staged", rollback_reason="test rollback list"
    )
    await session.flush()
    records = await list_rollback_records(session, lifecycle_record_id=r.id, limit=10)
    assert len(records) >= 1


@pytest.mark.asyncio
async def test_serialize_rollback_record(session):
    r = await discover_model(session, model_name="ser-rollback")
    await session.flush()
    await stage_model(session, r.id)
    await session.flush()
    await transition_lifecycle_state(session, r.id, target_state="pending_approval")
    await session.flush()
    rollback = await rollback_model(
        session, r.id, rollback_to_state="staged", rollback_reason="serialize test"
    )
    await session.flush()
    data = serialize_rollback_record(rollback)
    assert data["rollback_from_state"] == "pending_approval"
    assert data["rollback_to_state"] == "staged"
    assert len(data["verification_hash"]) == 12
    data_full = serialize_rollback_record(rollback, sensitive=True)
    assert len(data_full["verification_hash"]) == 64
