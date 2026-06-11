from __future__ import annotations

import logging
import os
import time
import uuid

import yaml
from app.core.config import get_settings
from app.core.request_context import (
    clear_correlation_id,
    clear_source_ip,
    clear_tenant_id,
    set_correlation_id,
    set_source_ip,
    set_tenant_id,
)
from app.db.session import get_redis
from app.services.rate_limit import (
    RateLimitExceeded,
    enforce_global_rate_limit,
    enforce_tenant_rate_limit,
)
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.routing import Match

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
    from app.services.backup.restore_lock_service import MaintenanceMode
    if MaintenanceMode.is_active():
        path = request.url.path
        is_allowed = (
            path in {"/health", "/ready", "/operational-readiness", "/status"}
            or path.startswith("/admin/backup")
            or path.startswith("/api/admin/backup")
            or path == "/admin/status"
            or path == "/admin/health/deep"
        )
        if not is_allowed:
            is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
            is_sensitive = path.startswith("/admin/") or path.startswith("/api/admin/")
            if is_write or is_sensitive:
                return JSONResponse(
                    {"detail": "Service Unavailable: system is undergoing maintenance restore"},
                    status_code=503
                )

    settings = get_settings()

    # Check payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_body_size_bytes:
        return JSONResponse({"detail": "request body too large"}, status_code=413)

    # SaaS Protection: Block dangerous endpoints
    if settings.deployment_mode == "saas":
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

    elif settings.public_exposure and (
        request.url.path in {"/admin-dashboard", "/admin-lab", "/provider-settings", "/tests"}
        or request.url.path.startswith("/static/admin/")
        or request.url.path.startswith("/static/admin-lab/")
        or request.url.path.startswith("/static/provider-settings/")
    ):
        detail = "provider settings disabled in public exposure mode"
        if "admin-lab" in request.url.path:
            detail = "admin lab disabled in public exposure mode"
        elif "admin-dashboard" in request.url.path or request.url.path.startswith("/static/admin/"):
            detail = "admin dashboard disabled in public exposure mode"
        return JSONResponse({"detail": detail}, status_code=404)

    # Extract tenant context (from header, auth will override later)
    tenant_id = request.headers.get("x-tenant-id", "").strip() or "default"
    request.state.tenant_id = tenant_id

    # Enforce Global Rate Limit (all deployment modes)
    try:
        redis = await get_redis()
        limit = settings.rate_limit_global_per_minute if hasattr(settings, 'rate_limit_global_per_minute') else 1000
        await enforce_global_rate_limit(redis, limit_per_minute=limit)
    except RateLimitExceeded as exc:
        return JSONResponse({"detail": str(exc)}, status_code=429)
    except Exception as e:
        logger.error(f"Global rate limit check failed (non-blocking): {e}")

    # Enforce Per-Tenant Rate Limit
    try:
        redis = await get_redis()
        tenant_rpm = getattr(settings, 'rate_limit_tenant_per_minute', 500)
        await enforce_tenant_rate_limit(redis, tenant_id, limit_per_minute=tenant_rpm)
    except RateLimitExceeded as exc:
        return JSONResponse({"detail": str(exc)}, status_code=429)
    except Exception as e:
        logger.error(f"Tenant rate limit check failed (non-blocking): {e}")

    correlation_id = request.headers.get("x-correlation-id", "").strip() or str(uuid.uuid4())
    source_ip = resolve_source_ip(request)
    request.state.correlation_id = correlation_id
    request.state.source_ip = source_ip
    set_correlation_id(correlation_id)
    set_source_ip(source_ip)
    set_tenant_id(tenant_id)
    
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        status_code = 500
        try:
            status_code = response.status_code
        except Exception:
            pass
        logger.info(
            f"HTTP {request.method} {request.url.path} - {status_code} - {latency_ms}ms - CID:{correlation_id} - IP:{source_ip}"
        )
        clear_correlation_id()
        clear_source_ip()
        clear_tenant_id()
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "object-src 'none'"
    )
    return response


_api_surface_cache = None

def _get_api_surface_map():
    global _api_surface_cache
    if _api_surface_cache is not None:
        return _api_surface_cache

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(current_dir, "../../config/api-surface.yaml"))
    
    mapping = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or []
                for entry in data:
                    key = (entry.get("path") or entry.get("endpoint"), entry.get("method"))
                    mapping[key] = entry
        except Exception as e:
            logger.error(f"Error loading api-surface.yaml: {e}")
    else:
        logger.warning(f"api-surface.yaml not found at {config_path}")
        
    _api_surface_cache = mapping
    return mapping


async def deprecation_middleware(request: Request, call_next):
    matched_route = None
    scope = request.scope
    
    # Try to match request to registered FastAPI routes
    for route in request.app.routes:
        try:
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                matched_route = route
                break
        except Exception:
            pass

    status = "supported"
    replacement = None
    sunset_date = None

    if matched_route:
        surface_map = _get_api_surface_map()
        key = (matched_route.path, request.method)
        if key in surface_map:
            entry = surface_map[key]
            status = entry.get("status", "supported")
            replacement = entry.get("replacement")
            sunset_date = entry.get("sunset_date")
            if status == "deprecated" and not sunset_date:
                sunset_date = "2026-12-31"

    response = await call_next(request)
    
    response.headers["X-API-Surface-Status"] = status
    if status == "deprecated":
        response.headers["X-Deprecated-Endpoint"] = "true"
        if replacement:
            response.headers["X-Replacement-Endpoint"] = replacement
        if sunset_date:
            response.headers["X-Sunset-Date"] = str(sunset_date)
            response.headers["Sunset"] = str(sunset_date)
        logger.warning(f"Deprecated endpoint accessed: {request.url.path}")
        
    # Inject Deprecation header for all legacy admin agent endpoints
    path = request.url.path
    if path == "/agents" or path.startswith("/agents/"):
        response.headers["Deprecation"] = "true"

    return response
