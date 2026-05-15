from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.request_context import clear_correlation_id, clear_source_ip, set_correlation_id, set_source_ip
from app.db.session import get_redis
from app.services.rate_limit import enforce_global_rate_limit, RateLimitExceeded

logger = logging.getLogger(__name__)


def resolve_source_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


async def request_context_middleware(request: Request, call_next):
    settings = get_settings()

    # Check payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_body_size_bytes:
        return JSONResponse({"detail": "request body too large"}, status_code=413)

    # SaaS Protection: Block dangerous endpoints and enforce global rate limit
    if settings.deployment_mode == "saas":
        # Block debug/internal endpoints in SaaS
        blocked_paths = {
            "/admin-lab", 
            "/admin/tests", 
            "/admin/readiness", 
            "/admin/security",
            "/admin/status/deep",
        }
        path = request.url.path
        if any(path == p or path.startswith(f"{p}/") for p in blocked_paths):
            return JSONResponse({"detail": "endpoint disabled in SaaS mode"}, status_code=403)
        
        # Enforce Global Rate Limit
        try:
            redis = await get_redis()
            await enforce_global_rate_limit(redis)
        except RateLimitExceeded as exc:
            return JSONResponse({"detail": str(exc)}, status_code=429)
        except Exception as e:
            # Don't fail the request if Redis is down for rate limiting, but log it
            logger.error(f"Global rate limit check failed: {e}")

    elif settings.public_exposure and (
        request.url.path in {"/admin-dashboard", "/admin-lab"}
        or request.url.path.startswith("/static/admin/")
        or request.url.path.startswith("/static/admin-lab/")
    ):
        detail = "admin lab disabled in public exposure mode" if "admin-lab" in request.url.path else "admin dashboard disabled in public exposure mode"
        return JSONResponse({"detail": detail}, status_code=404)
    correlation_id = request.headers.get("x-correlation-id", "").strip() or str(uuid.uuid4())
    source_ip = resolve_source_ip(request)
    request.state.correlation_id = correlation_id
    request.state.source_ip = source_ip
    set_correlation_id(correlation_id)
    set_source_ip(source_ip)
    
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        status_code = 500
        try:
            status_code = response.status_code
        except:
            pass
        logger.info(
            f"HTTP {request.method} {request.url.path} - {status_code} - {latency_ms}ms - CID:{correlation_id} - IP:{source_ip}"
        )
        clear_correlation_id()
        clear_source_ip()
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response
