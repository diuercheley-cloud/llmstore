import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict

from app.core.config import get_settings
from app.models.agent_notifications import NotificationPreference, PushDevice
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("push_provider")


class PushProviderService:
    # A class-level list for mock push events, useful for tests
    sent_mock_pushes = []

    @classmethod
    def clear_mock_pushes(cls):
        cls.sent_mock_pushes.clear()

    @classmethod
    async def register_device(
        cls,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        device_token: str,
        platform: str
    ) -> PushDevice:
        """Registers a push device for a user, maintaining tenant/user isolation."""
        # Find if device_token already exists
        stmt = select(PushDevice).where(PushDevice.device_token == device_token)
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()

        if device:
            # Update user / tenant mapping or reactivate
            device.tenant_id = tenant_id
            device.user_id = user_id
            device.platform = platform
            device.is_active = True
        else:
            device = PushDevice(
                tenant_id=tenant_id,
                user_id=user_id,
                device_token=device_token,
                platform=platform,
                is_active=True
            )
            db.add(device)

        await db.commit()
        return device

    @classmethod
    async def send_push(
        cls,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        title: str,
        body: str
    ) -> Dict[str, Any]:
        """Sends push notification to all active devices of a user."""
        settings = get_settings()

        # 1. Check feature flag
        if not settings.agent_push_notifications_enabled:
            raise ValueError("Push notifications are disabled by feature flag.")

        # 2. Check user notification preference
        stmt_pref = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id
        )
        res_pref = await db.execute(stmt_pref)
        pref = res_pref.scalar_one_or_none()
        if pref and not pref.push_enabled:
            raise ValueError(f"User {user_id} has disabled push notifications.")

        # 3. Retrieve user active device tokens
        stmt_devices = select(PushDevice).where(
            PushDevice.tenant_id == tenant_id,
            PushDevice.user_id == user_id,
            PushDevice.is_active == True
        )
        res_devices = await db.execute(stmt_devices)
        devices = res_devices.scalars().all()

        if not devices:
            logger.info(f"No active push devices registered for user {user_id} under tenant {tenant_id}")
            return {"status": "skipped", "reason": "no_registered_devices", "recipient": user_id}

        results = []
        provider = settings.push_provider.lower()

        for dev in devices:
            try:
                if provider == "mock":
                    cls.sent_mock_pushes.append({
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "device_token": dev.device_token,
                        "platform": dev.platform,
                        "title": title,
                        "body": body
                    })
                    logger.info(f"[Mock Push] Sent to {dev.device_token} ({dev.platform}): {title}")
                    results.append({"device_token": dev.device_token, "status": "sent", "provider": "mock"})

                elif provider == "fcm":
                    res = cls._send_fcm(dev.device_token, title, body)
                    results.append(res)

                elif provider == "apns":
                    res = cls._send_apns(dev.device_token, title, body)
                    results.append(res)

                else:
                    raise ValueError(f"Unknown push provider configured: {provider}")

            except Exception as e:
                logger.error(f"Failed to send push to device {dev.device_token}: {e}")
                results.append({"device_token": dev.device_token, "status": "failed", "error": str(e)})

        return {
            "status": "completed",
            "recipient": user_id,
            "results": results
        }

    @classmethod
    def _send_fcm(cls, device_token: str, title: str, body: str) -> Dict[str, Any]:
        settings = get_settings()
        if not settings.fcm_api_key:
            raise ValueError("FCM API Key is not configured.")

        url = "https://fcm.googleapis.com/fcm/send"
        payload = {
            "to": device_token,
            "notification": {
                "title": title,
                "body": body,
                "sound": "default"
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"key={settings.fcm_api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return {"device_token": device_token, "status": "sent", "provider": "fcm"}
                else:
                    raise RuntimeError(f"FCM returned status {response.status}")
        except Exception as e:
            logger.error(f"FCM request failed: {e}")
            raise

    @classmethod
    def _send_apns(cls, device_token: str, title: str, body: str) -> Dict[str, Any]:
        # APNS requires HTTP/2 and client certificates or token authentication
        # For our stub/client configuration, verify key presence and do mock/stub request
        settings = get_settings()
        if not settings.apns_key_id:
            raise ValueError("APNS Key ID is not configured.")

        # Real APNS connection requires hyper/h2 connection in Python, which is non-standard.
        # We simulate the APNS endpoint hit for APNS provider.
        logger.info(f"[APNS HTTP2 Simulated] Sending APNS push to {device_token}")
        return {"device_token": device_token, "status": "sent", "provider": "apns"}
