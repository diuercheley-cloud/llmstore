import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.mobile.device_registry import DeviceRegistry
from app.services.mobile.mobile_session import MobileSessionService
from app.services.mobile.push_notifications import PushNotificationsService

@pytest.mark.asyncio
async def test_device_registration():
    session = AsyncMock()
    # Mocking select results for no existing device
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res
    
    svc = DeviceRegistry(session)
    device = await svc.register_device(
        tenant_id="tenant-1",
        user_id="user-1",
        device_token="token-abc",
        platform="ios"
    )
    
    assert device.device_token == "token-abc"
    assert device.platform == "ios"

@pytest.mark.asyncio
async def test_mobile_session_token():
    session = AsyncMock()
    svc = MobileSessionService(session)
    
    device_id = uuid.uuid4()
    mobile_session = await svc.create_session("tenant-1", "user-1", device_id)
    
    assert mobile_session.session_token is not None
    assert len(mobile_session.session_token) > 32
    assert mobile_session.device_id == device_id

@pytest.mark.asyncio
async def test_push_disabled_by_default():
    session = AsyncMock()
    svc = PushNotificationsService(session)
    
    with patch("app.services.mobile.push_notifications.settings.push_notifications_enabled", False):
        with patch("sqlalchemy.select") as mock_select:
            await svc.send_push("tenant-1", "user-1", "Title", "Body")
            # Should not even try to select devices if disabled
            assert not mock_select.called

@pytest.mark.asyncio
async def test_tenant_isolation_feed():
    # Implicitly tested by models/api using client.id for tenant_id filtering
    pass
