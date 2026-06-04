
import pytest
from app.services.mobile.device_registry import DeviceRegistryService
from app.services.mobile.push_notifications import PushNotificationService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_device_registration(session: AsyncSession):
    svc = DeviceRegistryService(session)
    tenant_id = "test-tenant"
    user_id = "test-user"
    token = "device-token-123"
    
    # 1. Register device
    device = await svc.register_device(
        tenant_id=tenant_id,
        user_id=user_id,
        device_token=token,
        platform="ios",
        model="iPhone 15"
    )
    assert device.id is not None
    assert device.platform == "ios"
    
    # 2. Update same device
    updated = await svc.register_device(
        tenant_id=tenant_id,
        user_id=user_id,
        device_token=token,
        platform="ios",
        model="iPhone 15 Pro"
    )
    assert updated.id == device.id
    assert updated.model == "iPhone 15 Pro"
    
    # 3. List user devices
    devices = await svc.get_user_devices(tenant_id, user_id)
    assert len(devices) == 1
    assert devices[0].device_token == token

@pytest.mark.asyncio
async def test_push_subscription(session: AsyncSession):
    svc = PushNotificationService(session)
    tenant_id = "test-tenant"
    user_id = "test-user"
    endpoint = "https://fcm.googleapis.com/fcm/send/123"
    
    # 1. Subscribe
    sub = await svc.subscribe(
        tenant_id=tenant_id,
        user_id=user_id,
        endpoint=endpoint,
        p256dh="p256dh-key",
        auth="auth-secret"
    )
    assert sub.id is not None
    assert sub.is_active is True
    
    # 2. Unsubscribe
    await svc.unsubscribe(endpoint)
    assert sub.is_active is False
    
    # 3. Resubscribe
    await svc.subscribe(
        tenant_id=tenant_id,
        user_id=user_id,
        endpoint=endpoint,
        p256dh="p256dh-key-new",
        auth="auth-secret"
    )
    assert sub.is_active is True
    assert sub.p256dh == "p256dh-key-new"
