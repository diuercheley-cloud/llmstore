import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class PhoenixExporter:
    """
    Exports agent telemetry data to Apache Phoenix (Arize) for observability.
    Gracefully degrades when httpx is unavailable or endpoint is unreachable.
    """

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None and HAS_HTTPX:
            headers = {}
            if self.api_key:
                headers["api_key"] = self.api_key
            self._client = httpx.Client(base_url=self.endpoint, headers=headers, timeout=10.0)
        return self._client

    def export(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.endpoint:
            return {
                "backend": "phoenix",
                "accepted": False,
                "reason": "endpoint not configured",
                "payload": payload,
            }

        client = self._get_client()
        if not client:
            return {
                "backend": "phoenix",
                "accepted": False,
                "reason": "httpx not installed",
                "payload": payload,
            }

        try:
            response = client.post("/v1/traces", json=payload)
            if response.is_success:
                logger.debug(f"Exported trace to Phoenix ({len(str(payload))} bytes)")
                return {"backend": "phoenix", "accepted": True, "status_code": response.status_code}
            else:
                logger.warning(f"Phoenix export rejected: {response.status_code} {response.text}")
                return {
                    "backend": "phoenix",
                    "accepted": False,
                    "status_code": response.status_code,
                    "reason": response.text,
                }
        except Exception as e:
            logger.error(f"Phoenix export failed: {e}")
            return {"backend": "phoenix", "accepted": False, "reason": str(e), "payload": payload}

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
