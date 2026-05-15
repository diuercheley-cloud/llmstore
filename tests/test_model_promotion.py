import pytest

from app.services.models.model_lifecycle_manager import (
    discover_model,
    stage_model,
    transition_lifecycle_state,
)
from app.services.models.model_promotion import (
    approve_promotion_request,
    create_promotion_request,
    execute_promotion,
    list_promotion_requests,
    reject_promotion_request,
    serialize_promotion_request,
)


@pytest.mark.asyncio
async def test_create_promotion_request(session):
    record = await discover_model(session, model_name="promo-model", cluster_id="c1")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
        requested_by="ops",
        reason="Ready for approval",
    )
    await session.commit()
    assert req.status == "pending"
    assert req.request_type == "staged_to_pending"
    assert req.source_state == "staged"


@pytest.mark.asyncio
async def test_approve_promotion_request(session):
    record = await discover_model(session, model_name="approve-model")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
        requested_by="ops",
    )
    await session.flush()
    approved = await approve_promotion_request(
        session, req.id, approved_by="admin", approval_note="Looks good"
    )
    await session.commit()
    assert approved.status == "approved"
    assert approved.approval_count_received == 1


@pytest.mark.asyncio
async def test_multi_approval_promotion(session):
    record = await discover_model(session, model_name="multi-approve")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
        approval_count_required=2,
        requested_by="ops",
    )
    await session.flush()
    first = await approve_promotion_request(session, req.id, approved_by="a1")
    await session.flush()
    assert first.status == "pending"
    assert first.approval_count_received == 1
    second = await approve_promotion_request(session, req.id, approved_by="a2")
    await session.commit()
    assert second.status == "approved"
    assert second.approval_count_received == 2


@pytest.mark.asyncio
async def test_reject_promotion_request(session):
    record = await discover_model(session, model_name="reject-model")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
    )
    await session.flush()
    rejected = await reject_promotion_request(
        session, req.id, rejected_by="admin", reason="Not ready"
    )
    await session.commit()
    assert rejected.status == "rejected"


@pytest.mark.asyncio
async def test_execute_promotion(session):
    record = await discover_model(session, model_name="exec-model")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
        requested_by="ops",
    )
    await session.flush()
    await approve_promotion_request(session, req.id, approved_by="admin")
    await session.flush()
    result = await execute_promotion(session, req.id, executed_by="system")
    await session.commit()
    assert result["executed"] is True
    assert "receipt_hash" in result
    assert result["to_state"] == "pending_approval"


@pytest.mark.asyncio
async def test_execute_promotion_requires_approved(session):
    record = await discover_model(session, model_name="exec-fail-model")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
    )
    await session.flush()
    with pytest.raises(ValueError, match="must be approved"):
        await execute_promotion(session, req.id)


@pytest.mark.asyncio
async def test_invalid_promotion_type_raises(session):
    record = await discover_model(session, model_name="bad-type-model")
    await session.flush()
    with pytest.raises(ValueError, match="Invalid promotion request type"):
        await create_promotion_request(
            session,
            lifecycle_record_id=record.id,
            request_type="invalid_type",
            target_state="approved",
        )


@pytest.mark.asyncio
async def test_invalid_promotion_transition_raises(session):
    record = await discover_model(session, model_name="bad-trans-model")
    await session.flush()
    with pytest.raises(ValueError, match="Invalid promotion transition"):
        await create_promotion_request(
            session,
            lifecycle_record_id=record.id,
            request_type="staged_to_pending",
            target_state="promoted",
        )


@pytest.mark.asyncio
async def test_list_promotion_requests(session):
    record = await discover_model(session, model_name="list-promo")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
    )
    await session.flush()
    requests = await list_promotion_requests(session, limit=10)
    assert len(requests) >= 1


@pytest.mark.asyncio
async def test_serialize_promotion_request(session):
    record = await discover_model(session, model_name="ser-promo")
    await session.flush()
    await stage_model(session, record.id)
    await session.flush()
    req = await create_promotion_request(
        session,
        lifecycle_record_id=record.id,
        request_type="staged_to_pending",
        target_state="pending_approval",
    )
    await session.flush()
    data = serialize_promotion_request(req)
    assert data["request_type"] == "staged_to_pending"
    assert data["status"] == "pending"
