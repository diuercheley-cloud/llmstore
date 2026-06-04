import os

from app.main import app
from app.services.platform.surface_audit import SurfaceAuditService
from fastapi.testclient import TestClient


def test_deprecated_endpoint_headers():
    """Test that a deprecated endpoint returns the deprecation and sunset headers."""
    with TestClient(app) as client:
        # /admin/billing/invoices is marked as deprecated in api-surface.yaml
        response = client.get("/admin/billing/invoices")
        # Headers should be present regardless of response status code
        assert response.headers.get("X-Deprecated-Endpoint") == "true"
        assert response.headers.get("X-Sunset-Date") == "2026-12-31"
        assert response.headers.get("Sunset") == "2026-12-31"

def test_orphaned_services_detected():
    """Test that orphaned services (not imported/used in other modules) are detected."""
    service = SurfaceAuditService()
    
    # Create a temporary orphaned service file
    temp_service_dir = os.path.join(service.base_dir, "control_plane/app/services/platform")
    temp_service_path = os.path.join(temp_service_dir, "temp_orphaned_service.py")
    
    os.makedirs(temp_service_dir, exist_ok=True)
    with open(temp_service_path, "w", encoding="utf-8") as f:
        f.write("# Dummy orphaned service\nclass DummyOrphanedService:\n    pass\n")
        
    try:
        audit_results = service.run_audit()
        orphaned = audit_results["services"]["orphaned_services"]
        assert "platform/temp_orphaned_service.py" in orphaned
    finally:
        if os.path.exists(temp_service_path):
            os.remove(temp_service_path)

def test_duplicate_api_detected():
    """Test that duplicate/overlapping routes are detected."""
    from fastapi import APIRouter
    
    # Temporarily register duplicate routes
    router = APIRouter()
    
    @router.get("/test-duplicate-route-temp")
    def route1():
        return {"msg": "one"}
        
    @router.get("/test-duplicate-route-temp")
    def route2():
        return {"msg": "two"}
        
    app.include_router(router)
    
    try:
        service = SurfaceAuditService()
        audit_results = service.run_audit()
        duplicates = audit_results["apis"]["duplicates"]
        assert "GET /test-duplicate-route-temp" in duplicates
    finally:
        # Clean up registered routes
        app.routes[:] = [r for r in app.routes if not (getattr(r, "path", None) == "/test-duplicate-route-temp")]

def test_unregistered_surface_appears_in_report():
    """Test that unregistered/unsupported surface components appear in the unregistered routes list."""
    from fastapi import APIRouter
    
    # Temporarily register an unregistered route (not in api-surface.yaml)
    router = APIRouter()
    
    @router.get("/unregistered-route-temp-xyz")
    def route1():
        return {"msg": "temp"}
        
    app.include_router(router)
    
    try:
        service = SurfaceAuditService()
        audit_results = service.run_audit()
        unregistered = audit_results["apis"]["unregistered_routes"]
        assert "GET /unregistered-route-temp-xyz" in unregistered
    finally:
        app.routes[:] = [r for r in app.routes if not (getattr(r, "path", None) == "/unregistered-route-temp-xyz")]
