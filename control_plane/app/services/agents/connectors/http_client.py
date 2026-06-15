import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from typing import Any

import httpx
from app.services.agents.connectors.connector_mode import is_real_http_enabled
from app.services.agents.connectors.rate_limits import rate_limit_manager

logger = logging.getLogger("connector_http_client")


class ConnectorHTTPClient:
    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        connector_name: str,
        rate_limit_policy: dict[str, Any],
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.connector_name = connector_name
        self.rate_limit_policy = rate_limit_policy
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = headers or {}

    def _sanitize_log_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(
                    term in k.lower() for term in ["token", "secret", "key", "password", "auth"]
                ):
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
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        if not is_real_http_enabled():
            raise PermissionError(
                "Real HTTP calls are disabled (AGENT_CONNECTOR_REAL_HTTP_ENABLED=false)"
            )

        # Rate Limit Check
        if not rate_limit_manager.check_rate_limit(
            self.tenant_id, self.connector_name, self.rate_limit_policy
        ):
            raise RuntimeError(f"Rate limit exceeded for connector {self.connector_name}")

        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {**self.headers, **(extra_headers or {})}

        if idempotency_key and method.upper() in ["POST", "PUT", "PATCH"]:
            # Standard idempotency headers (Stripe style or custom)
            headers["Idempotency-Key"] = idempotency_key
            headers["X-Idempotency-Key"] = idempotency_key

        # Log request (sanitized)
        logger.info(
            f"Connector Request: {method} {url} | Params: {self._sanitize_log_data(params)} | Headers: {self._sanitize_log_data(headers)}"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_data,
                        headers=headers,
                        **kwargs,
                    )

                    # Log response status
                    logger.info(
                        f"Connector Response: {method} {url} | Status: {response.status_code}"
                    )

                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        wait_time = (
                            int(retry_after)
                            if retry_after and retry_after.isdigit()
                            else (2**attempt)
                        )
                        logger.warning(f"Rate limited (429), retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code >= 500 and attempt < self.max_retries:
                        wait_time = 2**attempt  # exponential backoff
                        logger.warning(
                            f"Server error {response.status_code}, retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
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
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)

        return {"error": "request_failed"}

    async def paginate(
        self,
        method: str,
        path: str,
        extract_list: Callable[[dict[str, Any]], list[Any]],
        next_page_params: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any] | None],
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """
        Generic async generator for paginated results.
        """
        current_params = (params or {}).copy()

        while True:
            result = await self.request(method, path, params=current_params, **kwargs)
            items = extract_list(result)

            for item in items:
                yield item

            new_params = next_page_params(result, current_params)
            if not new_params:
                break
            current_params.update(new_params)
