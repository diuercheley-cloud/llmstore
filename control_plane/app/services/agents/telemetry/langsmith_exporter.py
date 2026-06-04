import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class LangsmithExporter:
    """
    Exports agent telemetry to LangSmith for tracing and evaluation.
    Supports both HTTP API and fallback modes.
    """

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None and HAS_HTTPX and self.api_url:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self._client = httpx.Client(base_url=self.api_url, headers=headers, timeout=10.0)
        return self._client

    def export(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_url:
            return {"backend": "langsmith", "accepted": False, "reason": "api_url not configured", "payload": payload}

        client = self._get_client()
        if not client:
            return {"backend": "langsmith", "accepted": False, "reason": "httpx not installed or no api_url", "payload": payload}

        try:
            response = client.post("/runs", json=payload)
            if response.is_success:
                logger.debug(f"Exported run to LangSmith ({len(str(payload))} bytes)")
                return {"backend": "langsmith", "accepted": True, "status_code": response.status_code}
            else:
                logger.warning(f"LangSmith export rejected: {response.status_code} {response.text}")
                return {"backend": "langsmith", "accepted": False, "status_code": response.status_code, "reason": response.text}
        except Exception as e:
            logger.error(f"LangSmith export failed: {e}")
            return {"backend": "langsmith", "accepted": False, "reason": str(e), "payload": payload}

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
