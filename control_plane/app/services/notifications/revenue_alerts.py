from __future__ import annotations

import logging
from typing import Any

import httpx
from app.core.config import get_settings
from app.services.routing.commercial_report_export import sanitize_report_payload

logger = logging.getLogger(__name__)


def build_revenue_alert_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return sanitize_report_payload(payload or {})


async def send_revenue_alert(payload: dict[str, Any] | None) -> dict[str, Any]:
    settings = get_settings()
    sanitized = build_revenue_alert_payload(payload)

    logger.info(
        "revenue_protection_alert",
        extra={"extra_data": {"payload": sanitized, "webhook_enabled": settings.commercial_revenue_protection_webhook_enabled}},
    )

    if not settings.commercial_revenue_protection_webhook_enabled:
        return {"status": "internal_only", "payload": sanitized}

    if not settings.commercial_revenue_protection_webhook_url:
        return {"status": "dry_run", "payload": sanitized}

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(settings.commercial_revenue_protection_webhook_url, json=sanitized)
    return {"status": "sent", "code": response.status_code}
