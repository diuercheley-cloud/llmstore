import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WebhookManager:
    """
    Manages optional webhooks for LLM harness events.
    """

    def __init__(self, url: str | None = None, enabled_events: list[str] | None = None):
        self.url = url
        self.enabled_events = enabled_events or ["run.started", "run.completed", "run.failed"]
        self.is_enabled = bool(url)

    async def send_event(self, event_type: str, payload: dict[str, Any]):
        if not self.is_enabled or not self.url or event_type not in self.enabled_events:
            return

        # Sanitize payload (simple redaction logic)
        sanitized_payload = self._sanitize(payload)

        data = {"event": event_type, "payload": sanitized_payload}

        # Async send with short retry
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(self.url, json=data)
                    response.raise_for_status()
                    break
            except Exception as e:
                if attempt == max_retries:
                    logger.warning(
                        f"Failed to send webhook to {self.url} after {max_retries} attempts: {e}"
                    )
                else:
                    await asyncio.sleep(1)

    def _sanitize(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: self._sanitize(v)
                for k, v in data.items()
                if k not in ("api_key", "secret", "token")
            }
        elif isinstance(data, list):
            return [self._sanitize(i) for i in data]
        return data
