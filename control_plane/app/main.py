import logging
from pathlib import Path
from fastapi.staticfiles import StaticFiles

from app.bootstrap.app_factory import create_app
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.runtime_security import validate_runtime_security

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
validate_runtime_security(settings)

# Print operational modes banner
try:
    from app.services.platform.deployment_modes import DeploymentModeService
    mode_svc = DeploymentModeService()
    mode_svc.print_startup_banner(settings)
except Exception as e:
    logger.error(f"Failed to print startup banner: {e}")

app = create_app()

# Mount static files - DEPRECATED for legacy UIs, keep only for essential assets
# TODO: Remove these mounts and migrate to NGINX/Caddy
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

import warnings

# Deprecation shim for legacy static admin UI — REMOVAL v3.0 (2026-12-31)
@app.get("/static/admin", include_in_schema=False)
async def deprecate_legacy_admin():
    warnings.warn(
        "Legacy Admin UI (/static/admin) is deprecated since v2.0 and will be removed in v3.0. "
        "Use the new Admin Dashboard at /admin instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning("Legacy Admin UI access detected (will be removed in v3.0). Use /admin instead.")
    return {"message": "Deprecated (removal: v3.0). Please use the new Admin Dashboard at /admin"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.control_plane_host,
        port=settings.control_plane_port,
        reload=settings.debug,
    )
