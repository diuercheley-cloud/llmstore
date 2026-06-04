import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import jwt
from app.core.config import get_settings
from app.models.commercial_cluster_registry import CommercialClusterRegistry
from app.models.commercial_cross_cluster_forwarding_event import (
    CommercialCrossClusterForwardingEvent,
)
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

cfg = get_settings()

# In-memory circuit breaker state: cluster_id -> {"state": "closed", "failures": 0, "last_failure": 0}
_circuit_breakers: Dict[str, Dict[str, Any]] = {}

class CommercialCrossClusterForwarder:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_cb_state(self, cluster_id: str) -> Dict[str, Any]:
        if cluster_id not in _circuit_breakers:
            _circuit_breakers[cluster_id] = {"state": "closed", "failures": 0, "last_failure": 0}
        return _circuit_breakers[cluster_id]

    def is_circuit_open(self, cluster_id: str) -> bool:
        if not cfg.commercial_cross_cluster_forwarding_circuit_breaker_enabled:
            return False
        cb = self._get_cb_state(cluster_id)
        if cb["state"] == "open":
            now = time.time()
            if now - cb["last_failure"] > cfg.commercial_cross_cluster_forwarding_circuit_breaker_reset_seconds:
                cb["state"] = "half_open"
                return False
            return True
        return False

    def mark_success(self, cluster_id: str):
        cb = self._get_cb_state(cluster_id)
        cb["state"] = "closed"
        cb["failures"] = 0

    def mark_failure(self, cluster_id: str):
        cb = self._get_cb_state(cluster_id)
        cb["failures"] += 1
        cb["last_failure"] = time.time()
        if cb["failures"] >= cfg.commercial_cross_cluster_forwarding_circuit_breaker_failure_threshold:
            cb["state"] = "open"

    def should_forward_request(self, target_cluster: CommercialClusterRegistry, qos_tier: Any | None = None) -> bool:
        if not cfg.commercial_cross_cluster_forwarding_enabled:
            return False
        if cfg.commercial_cross_cluster_forwarding_mode == "disabled":
            return False

        # Phase 20: QoS Tier Enforcement
        if qos_tier and not qos_tier.allow_cross_cluster:
            return False

        if not target_cluster.forwarding_enabled:
            return False
        if target_cluster.forwarding_status != "healthy":
            return False
        if not target_cluster.forwarding_base_url:
            return False
        if self.is_circuit_open(target_cluster.cluster_id):
            return False
        return True

    def generate_internal_jwt(self, audience: Optional[str]) -> str:
        # Simplified internal JWT generation
        payload = {
            "iss": "local_cluster",
            "aud": audience or "cross_cluster",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "type": "cross_cluster_forwarding"
        }
        # Ideally signed with a private key, here we use a secret or just simple symmetric for demo
        # In a real impl, we'd use RSA
        secret = cfg.secret_key if hasattr(cfg, "secret_key") else "internal_secret"
        return jwt.encode(payload, secret, algorithm="HS256")

    def build_forward_headers(self, original_headers: httpx.Headers, target_cluster: CommercialClusterRegistry, correlation_id: str) -> dict:
        headers = {}
        for k, v in original_headers.items():
            # DO NOT forward authorization
            if k.lower() not in ["authorization", "host", "content-length"]:
                headers[k.lower()] = v
        
        headers["x-cross-cluster-correlation-id"] = correlation_id
        headers["x-forwarded-for-cluster"] = "local" # could be local cluster id
        
        if cfg.commercial_cross_cluster_forwarding_require_jwt:
            token = self.generate_internal_jwt(target_cluster.forwarding_jwt_audience)
            headers["x-internal-forwarding-auth"] = f"Bearer {token}"
            
        return headers

    async def forward_request(self, request: Request, target_cluster: CommercialClusterRegistry, body: bytes) -> Optional[Response]:
        """
        Attempts to forward the request to target_cluster.
        If it fails, returns None (caller should fallback local).
        """
        if cfg.commercial_cross_cluster_forwarding_mode == "dry_run":
            # Just pretend it worked or let caller fallback local silently
            return None

        correlation_id = str(uuid.uuid4())
        start_time = time.time()
        url = f"{target_cluster.forwarding_base_url.rstrip('/')}{request.url.path}"

        headers = self.build_forward_headers(request.headers, target_cluster, correlation_id)
        timeout = cfg.commercial_cross_cluster_forwarding_timeout_seconds
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Check for error
                if resp.status_code >= 500:
                    self.mark_failure(target_cluster.cluster_id)
                    await self._record_event(target_cluster.cluster_id, correlation_id, "non_stream", "fallback_local", latency_ms, len(body), 0)
                    return None
                    
                self.mark_success(target_cluster.cluster_id)
                await self._record_event(target_cluster.cluster_id, correlation_id, "non_stream", "forwarded", latency_ms, len(body), len(resp.content))
                
                return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
        except Exception as e:
            logger.warning(f"Cross-cluster forward failure: {e}")
            self.mark_failure(target_cluster.cluster_id)
            latency_ms = int((time.time() - start_time) * 1000)
            await self._record_event(target_cluster.cluster_id, correlation_id, "non_stream", "fallback_local", latency_ms, len(body), 0)
            return None

    async def stream_sse_forward(self, request: Request, target_cluster: CommercialClusterRegistry, body: bytes) -> Optional[StreamingResponse]:
        if cfg.commercial_cross_cluster_forwarding_mode == "dry_run":
            return None

        correlation_id = str(uuid.uuid4())
        url = f"{target_cluster.forwarding_base_url.rstrip('/')}{request.url.path}"
        headers = self.build_forward_headers(request.headers, target_cluster, correlation_id)
        timeout = cfg.commercial_cross_cluster_forwarding_stream_timeout_seconds

        client = httpx.AsyncClient(timeout=timeout)
        start_time = time.time()
        try:
            req = client.build_request(request.method, url, headers=headers, content=body)
            resp = await client.send(req, stream=True)
            
            if resp.status_code >= 500:
                self.mark_failure(target_cluster.cluster_id)
                await resp.aclose()
                await client.aclose()
                return None
            
            self.mark_success(target_cluster.cluster_id)

            async def _stream_generator() -> AsyncGenerator[bytes, None]:
                bytes_in = 0
                try:
                    async for chunk in resp.aiter_bytes():
                        bytes_in += len(chunk)
                        yield chunk
                finally:
                    await resp.aclose()
                    await client.aclose()
                    latency_ms = int((time.time() - start_time) * 1000)
                    # We can't await inside sync generator if we use Fastapi streaming correctly, but streamingresponse generator is async.
                    # For recording async in an async generator:
                    await self._record_event_safe(target_cluster.cluster_id, correlation_id, "stream", "forwarded", latency_ms, len(body), bytes_in)

            return StreamingResponse(_stream_generator(), status_code=resp.status_code, headers=dict(resp.headers))

        except Exception as e:
            logger.warning(f"Cross-cluster SSE forward failure: {e}")
            await client.aclose()
            self.mark_failure(target_cluster.cluster_id)
            latency_ms = int((time.time() - start_time) * 1000)
            await self._record_event(target_cluster.cluster_id, correlation_id, "stream", "fallback_local", latency_ms, len(body), 0)
            return None

    async def _record_event(self, target_cluster_id: str, correlation_id: str, mode: str, result: str, latency: int, bytes_out: int, bytes_in: int):
        event = CommercialCrossClusterForwardingEvent(
            source_cluster_id="local",
            target_cluster_id=target_cluster_id,
            correlation_id=correlation_id,
            request_mode=mode,
            result=result,
            latency_ms=latency,
            bytes_out=bytes_out,
            bytes_in=bytes_in
        )
        self.db.add(event)
        await self.db.commit()

    async def _record_event_safe(self, target_cluster_id: str, correlation_id: str, mode: str, result: str, latency: int, bytes_out: int, bytes_in: int):
        try:
            await self._record_event(target_cluster_id, correlation_id, mode, result, latency, bytes_out, bytes_in)
        except Exception:
            pass # ignore in streaming
