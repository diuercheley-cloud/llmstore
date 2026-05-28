import httpx
import logging
import json
import time
from typing import Any, Dict, Optional, List
from app.services.agents.connectors.connector_mode import is_real_http_enabled

logger = logging.getLogger("connector_http_client")

class ConnectorHTTPClient:
    def __init__(
        self, 
        base_url: str, 
        timeout: float = 30.0, 
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = headers or {}

    def _sanitize_log_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(term in k.lower() for term in ["token", "secret", "key", "password", "auth"]):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = self._sanitize_log_data(v)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_log_data(item) for item in data]
        return data

    async def request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        if not is_real_http_enabled():
            raise PermissionError("Real HTTP calls are disabled (AGENT_CONNECTOR_REAL_HTTP_ENABLED=false)")

        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {**self.headers, **(extra_headers or {})}

        # Log request (sanitized)
        logger.info(f"Connector Request: {method} {url} | Params: {self._sanitize_log_data(params)} | Headers: {self._sanitize_log_data(headers)}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_data,
                        headers=headers,
                        **kwargs
                    )
                    
                    # Log response status
                    logger.info(f"Connector Response: {method} {url} | Status: {response.status_code}")

                    if response.status_code >= 500 and attempt < self.max_retries:
                        wait_time = (2 ** attempt)  # exponential backoff
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    return response.json()

                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
                    if attempt == self.max_retries:
                        raise
                except Exception as e:
                    logger.error(f"Request Error: {str(e)}")
                    if attempt == self.max_retries:
                        raise
                    wait_time = (2 ** attempt)
                    time.sleep(wait_time)

        return {"error": "request_failed"}
