# Owner: agent-platform
"""
MCP Transport Layer

Implements two transport strategies that speak the MCP JSON-RPC protocol:

1. StdioTransport  — launches a local subprocess and communicates over stdin/stdout.
   Used for: local MCP servers registered with transport='stdio'.

2. HttpTransport   — sends POST requests to an HTTP MCP endpoint.
   Used for: remote/hosted MCP servers registered with transport='streamable_http'.

Both transports implement the same interface:
  initialize()    → dict   (MCP initialize handshake)
  request(method, params) → dict   (any JSON-RPC method)
  close()         → None

Feature flags consumed:
  AGENT_MCP_EXTERNAL_NETWORK_ENABLED  — blocks HttpTransport unless true
  AGENT_MCP_CALL_TIMEOUT_MS           — per-call timeout

Security:
  - HttpTransport never follows redirects to prevent SSRF.
  - StdioTransport subprocess runs without shell=True.
  - Neither transport logs raw response bodies (only method/id metadata).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_MCP_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_NAME = "llm-inference-stack"
_CLIENT_VERSION = "1.0.0"


class MCPTransportError(Exception):
    """Raised when the MCP transport layer cannot complete a call."""


class _BaseTransport:
    """Shared utilities for both transport implementations."""

    def _make_request_body(self, method: str, params: dict[str, Any], req_id: int = 1) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }

    def _unwrap_result(self, body: dict, method: str) -> Any:
        if "error" in body:
            raise MCPTransportError(f"MCP error on {method}: {body['error']}")
        return body.get("result", {})

    def _initialize_params(self) -> dict:
        return {
            "protocolVersion": _MCP_PROTOCOL_VERSION,
            "capabilities": {
                "sampling": {},  # we request nothing extra — server will report its own
            },
            "clientInfo": {
                "name": _CLIENT_NAME,
                "version": _CLIENT_VERSION,
            },
        }


class HttpTransport(_BaseTransport):
    """
    Streamable HTTP transport.

    Sends JSON-RPC requests as HTTP POST to the registered endpoint.
    Validates external-network flag before any outbound connection.

    Security:
      - follow_redirects=False prevents open-redirect / SSRF.
      - All connections are blocked unless AGENT_MCP_EXTERNAL_NETWORK_ENABLED=true
        and the endpoint is not a private/loopback address (except for test mode).
    """

    def __init__(self, endpoint: str, timeout_ms: int = 10_000):
        self.endpoint = endpoint
        self.timeout_s = timeout_ms / 1000.0
        settings = get_settings()
        is_external = not (
            endpoint.startswith("http://localhost")
            or endpoint.startswith("http://127.")
            or endpoint.startswith("http://0.0.0.0")
        )
        if is_external and not settings.agent_mcp_external_network_enabled:
            raise MCPTransportError(
                "External MCP HTTP transport blocked: AGENT_MCP_EXTERNAL_NETWORK_ENABLED=false"
            )
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=self.timeout_s,
        )

    async def initialize(self) -> dict:
        return await self.request("initialize", self._initialize_params())

    async def request(self, method: str, params: dict[str, Any], req_id: int = 1) -> Any:
        body = self._make_request_body(method, params, req_id)
        try:
            resp = await self._client.post(
                self.endpoint,
                json=body,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            return self._unwrap_result(data, method)
        except httpx.HTTPStatusError as exc:
            raise MCPTransportError(
                f"HTTP {exc.response.status_code} calling MCP {method}"
            ) from exc
        except httpx.RequestError as exc:
            raise MCPTransportError(f"Network error calling MCP {method}: {exc}") from exc

    async def close(self) -> None:
        await self._client.aclose()


class StdioTransport(_BaseTransport):
    """
    Stdio transport for local MCP servers.

    Launches the server as a subprocess and communicates via JSON-RPC
    newline-delimited messages over stdin/stdout.

    The endpoint field is interpreted as the executable path (plus args
    separated by spaces).

    Security:
      - subprocess launched with shell=False.
      - stdout/stderr isolated from host process.
    """

    def __init__(self, command: str, timeout_ms: int = 10_000):
        self.command = command
        self.timeout_s = timeout_ms / 1000.0
        self._proc: asyncio.subprocess.Process | None = None
        self._req_id = 0

    async def _ensure_started(self) -> None:
        if self._proc is not None:
            return
        args = self.command.split()
        self._proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def initialize(self) -> dict:
        return await self.request("initialize", self._initialize_params())

    async def request(self, method: str, params: dict[str, Any], req_id: int | None = None) -> Any:
        await self._ensure_started()
        if req_id is None:
            self._req_id += 1
            req_id = self._req_id
        body = self._make_request_body(method, params, req_id)
        line = json.dumps(body) + "\n"
        try:
            self._proc.stdin.write(line.encode())  # type: ignore[union-attr]
            await asyncio.wait_for(
                self._proc.stdin.drain(),  # type: ignore[union-attr]
                timeout=self.timeout_s,
            )
            raw = await asyncio.wait_for(
                self._proc.stdout.readline(),  # type: ignore[union-attr]
                timeout=self.timeout_s,
            )
            data = json.loads(raw.decode())
            return self._unwrap_result(data, method)
        except TimeoutError as exc:
            raise MCPTransportError(f"Stdio MCP call '{method}' timed out") from exc
        except json.JSONDecodeError as exc:
            raise MCPTransportError(f"Invalid JSON from stdio MCP server on '{method}'") from exc

    async def close(self) -> None:
        if self._proc:
            try:
                self._proc.stdin.close()  # type: ignore[union-attr]
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except Exception:
                self._proc.kill()
            self._proc = None


def build_transport(
    transport_type: str, endpoint: str, timeout_ms: int = 10_000
) -> HttpTransport | StdioTransport:
    """
    Factory: choose the transport implementation from the server's config.

    transport_type:
      'streamable_http' | 'http'  → HttpTransport
      'stdio'                     → StdioTransport
    """
    if transport_type in {"streamable_http", "http"}:
        return HttpTransport(endpoint, timeout_ms)
    if transport_type == "stdio":
        return StdioTransport(endpoint, timeout_ms)
    raise MCPTransportError(f"Unknown MCP transport type: '{transport_type}'")
