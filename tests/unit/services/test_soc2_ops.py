from datetime import UTC, datetime, timedelta

import pytest
from app.services.soc2_control_operations import SOC2ControlOperationsService


@pytest.mark.asyncio
async def test_access_review_validation(db_session):
    service = SOC2ControlOperationsService(db_session)

    # Missing reviewer
    invalid_data = {"owner": "CISO", "period_start": datetime.now(UTC)}
    with pytest.raises(ValueError, match="must have a designated reviewer"):
        await service.create_access_review(invalid_data)


@pytest.mark.asyncio
async def test_exception_validation(db_session):
    service = SOC2ControlOperationsService(db_session)

    # Missing expiration
    invalid_data = {"control_id": "CC6.1", "reason": "Legacy system"}
    with pytest.raises(ValueError, match="must have an expiration date"):
        await service.create_exception(invalid_data)


@pytest.mark.asyncio
async def test_expired_exception_detection(db_session):
    service = SOC2ControlOperationsService(db_session)

    # Create expired exception
    expired_date = datetime.now(UTC) - timedelta(days=1)
    await service.create_exception(
        {"control_id": "CC7.1", "reason": "Test", "owner": "SRE", "expiration_date": expired_date}
    )

    expired_list = await service.check_expired_exceptions()
    assert len(expired_list) == 1
    assert expired_list[0].status == "expired"
